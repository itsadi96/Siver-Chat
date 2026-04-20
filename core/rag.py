import os
from pathlib import Path
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from textwrap import shorten

class RAGManager:
    def __init__(self, index_dir="vectorstore", doc_dir="documents"):
        self.index_dir = index_dir
        self.doc_dir = doc_dir
        self.embed_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embeddings = None
        self.db = None
        
        os.makedirs(self.index_dir, exist_ok=True)
        os.makedirs(self.doc_dir, exist_ok=True)
        
        self.load_index()

    def get_embeddings(self):
        if not self.embeddings:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embed_model_name)
        return self.embeddings

    def load_index(self):
        """Loads FAISS index from disk if it exists."""
        if os.path.exists(os.path.join(self.index_dir, "index.faiss")):
            try:
                self.db = FAISS.load_local(self.index_dir, self.get_embeddings(), allow_dangerous_deserialization=True)
                return True
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
        return False

    def load_document(self, path: Path) -> str:
        """Parse raw text from a given document."""
        suffix = path.suffix.lower()
        try:
            if suffix in {".txt", ".md"}:
                return path.read_text(encoding="utf-8", errors="ignore")
            elif suffix == ".pdf":
                reader = PdfReader(str(path))
                return "\n".join([page.extract_text() or "" for page in reader.pages])
            elif suffix == ".csv":
                import csv
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    return "\n".join([", ".join(row) for row in reader])
        except Exception as e:
            print(f"Error loading {path.name}: {e}")
        return ""

    def chunk_text(self, text: str):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,
            chunk_overlap=120,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        return splitter.split_text(text)

    def build_index(self) -> str:
        """Processes files in documents/ and saves FAISS vectors."""
        chunks = []
        metadatas = []
        doc_path = Path(self.doc_dir)
        files = [f for f in doc_path.glob("**/*") if f.is_file()]
        
        if not files:
            return "No files found in documents/ folder."
            
        for file in files:
            text = self.load_document(file)
            if not text.strip():
                continue
            text_chunks = self.chunk_text(text)
            chunks.extend(text_chunks)
            metadatas.extend([{"source": file.name}] * len(text_chunks))
            
        if not chunks:
            return "No valid text could be extracted."
            
        self.db = FAISS.from_texts(chunks, self.get_embeddings(), metadatas=metadatas)
        self.db.save_local(self.index_dir)
        return f"✅ Ingested {len(files)} file(s) into {len(chunks)} chunks."

    def search_context(self, query: str, top_k: int = 4):
        """Returns structured context strings and source citations."""
        if not self.db:
            return None, [], []
            
        try:
            docs = self.db.similarity_search(query, k=top_k)
            if not docs:
                return None, [], []
                
            evidence = []
            sources = []
            context_parts = []
            
            for idx, doc in enumerate(docs, start=1):
                content = (doc.page_content or "").strip()
                if not content:
                    continue
                src = doc.metadata.get("source", "unknown")
                if src not in sources:
                    sources.append(src)
                    
                snippet = shorten(content.replace("\n", " "), width=280, placeholder="...")
                evidence.append({"rank": idx, "source": src, "snippet": snippet})
                context_parts.append(f"[{idx}] {content}")
                
            context_str = "\n\n".join(context_parts)
            return context_str, sources, evidence
        except Exception as e:
            print(f"Error searching vector DB: {e}")
            return None, [], []
