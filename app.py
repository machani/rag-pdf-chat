import streamlit as st
import os
from modules.rag_engine import load_and_split_pdfs, create_vector_store, get_rag_chain, query_rag
import modules.db_manager as db_manager

st.set_page_config(page_title="RAG PDF Chat", layout="wide")

st.title("📄 PDF Chat with RAG")

# Initialize DB (Handles migration if needed)
db_manager.init_db()

# --- Session Management Helper ---
def select_session(session_id):
    st.session_state.current_session_id = session_id
    st.session_state.messages = db_manager.load_history(session_id)
    # Clear processed files state when switching sessions so user can upload new docs for this session if needed
    # (Optional: In this simple app, vector store is global or per-run, so we might want to keep it.)
    # For now, let's just reload messages.

def create_new_session():
    new_id = db_manager.create_session(f"Chat {len(db_manager.get_sessions()) + 1}")
    select_session(new_id)

def delete_session_btn(session_id):
    db_manager.delete_session(session_id)
    # If deleted current session, switch to another or create new
    if st.session_state.current_session_id == session_id:
        sessions = db_manager.get_sessions()
        if sessions:
            select_session(sessions[0]["id"])
        else:
            create_new_session()
    else:
        st.rerun()

# --- Sidebar ---
with st.sidebar:
    st.header("Upload Document")
    uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    
    st.divider()
    
    st.header("Chat Sessions")
    if st.button("➕ New Chat", use_container_width=True):
        create_new_session()
        st.rerun()
    
    # Load Sessions
    sessions = db_manager.get_sessions()
    if not sessions:
        # Create default session if none exist
        create_new_session()
        sessions = db_manager.get_sessions()
        
    # Ensure current_session_id is set
    if "current_session_id" not in st.session_state:
        if sessions:
            select_session(sessions[0]["id"])
        else:
            create_new_session()

    # Display Session List
    for sess in sessions:
        col1, col2 = st.columns([0.8, 0.2])
        is_active = sess["id"] == st.session_state.get("current_session_id")
        
        # Simple styling for active session
        label = f"**{sess['title']}**" if is_active else sess['title']
        
        if col1.button(label, key=f"sess_{sess['id']}_btn"):
            select_session(sess["id"])
            st.rerun()
            
        if col2.button("🗑️", key=f"del_{sess['id']}_btn"):
            delete_session_btn(sess["id"])
            st.rerun()

# --- Main Chat Area ---

# Initialize Vector Store (Persistent attempt)
if "rag_chain" not in st.session_state:
    if os.path.exists("./data/chroma_db"):
        with st.spinner("Loading persistent knowledge base..."):
            vectorstore = create_vector_store(None)
            st.session_state.vectorstore = vectorstore
            st.session_state.rag_chain = get_rag_chain(vectorstore)
            st.toast("Loaded existing knowledge base!", icon="📚")

# Display Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Display sources if available in metadata
        if message.get("metadata") and "sources" in message["metadata"]:
            with st.expander("📚 Sources"):
                for idx, doc in enumerate(message["metadata"]["sources"]):
                    # Handle both dict (from DB) and Document object (from memory before save) cases?
                    # Actually, we should standardize. When saving, we convert to dict. 
                    # When reading from DB, it's already dict.
                    # Current code in app logic handles Document objects. We need to serialize them for DB.
                    
                    # If it's loaded from DB, it's a dict.
                    source_name = doc.get("source", "Unknown file")
                    page_num = doc.get("page", "Unknown page")
                    content_snippet = doc.get("content", "")
                    
                    st.markdown(f"**Source {idx+1}**: {source_name} (Page {page_num})")
                    st.text(content_snippet[:200] + "...")

# Process Uploaded Files
if uploaded_files:
    current_file_names = sorted([f.name for f in uploaded_files])
    
    if "processed_file_names" not in st.session_state or st.session_state.processed_file_names != current_file_names:
        with st.spinner("Processing PDFs..."):
            temp_dir = "data/temp_pdf"
            os.makedirs(temp_dir, exist_ok=True)
            
            file_paths = []
            for uploaded_file in uploaded_files:
                temp_file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_paths.append(temp_file_path)
            
            splits = load_and_split_pdfs(file_paths)
            vectorstore = create_vector_store(splits)
            st.session_state.vectorstore = vectorstore
            st.session_state.rag_chain = get_rag_chain(vectorstore)
            st.session_state.processed_file_names = current_file_names
            
            st.success(f"Processed {len(uploaded_files)} PDF(s)! You can now ask questions.")

# Chat Input
if prompt := st.chat_input("Ask a question about the PDF..."):
    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Save user message
    db_manager.save_message(st.session_state.current_session_id, "user", prompt)

    # Generate Response
    if "rag_chain" in st.session_state:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare history for RAG (last 5 messages to avoid blowing context)
                history_tuples = [(msg["role"], msg["content"]) for msg in st.session_state.messages[-6:-1]]
                
                response = query_rag(st.session_state.rag_chain, prompt, history=history_tuples)
                answer = response["answer"]
                st.markdown(answer)
                
                sources_data = []
                if "sources" in response and response["sources"]:
                    with st.expander("📚 Sources"):
                        for idx, doc in enumerate(response["sources"]):
                            # 'doc' is a Document object here.
                            source_name = doc.metadata.get("source", "Unknown file")
                            page_num = doc.metadata.get("page", "Unknown page")
                            st.markdown(f"**Source {idx+1}**: {source_name} (Page {page_num})")
                            st.text(doc.page_content[:200] + "...")
                            
                            # Prepare for DB storage
                            sources_data.append({
                                "source": source_name,
                                "page": page_num,
                                "content": doc.page_content
                            })
        
        # Assistant message object
        assistant_msg = {
            "role": "assistant", 
            "content": answer,
            "metadata": {"sources": sources_data}
        }
        st.session_state.messages.append(assistant_msg)
        
        # Save assistant message
        db_manager.save_message(
            st.session_state.current_session_id, 
            "assistant", 
            answer, 
            metadata={"sources": sources_data}
        )
            
    else:
        st.error("Please upload PDF files or ensure the knowledge base is loaded.")
