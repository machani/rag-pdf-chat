# RAG PDF Chat

A robust **Retrieval-Augmented Generation (RAG)** application that allows you to chat with your PDF documents using AI.

## Features

- **📄 Document Ingestion**: Upload multiple PDF files simultaneously. The app processes, chunks, and indexes them for retrieval.
- **💬 Interactive Chat**: Chat with your documents using a familiar messaging interface powered by Streamlit.
- **🧠 Context-Aware Answers**: Uses **LangChain** and **OpenAI (GPT-4o)** to provide accurate answers based strictly on the content of your PDFs.
- **📚 Source Citations**: Every response includes precise citations with source document names and page numbers, fostering transparency and verification.
- **💾 Session Management**: Create, named, and switch between multiple chat sessions. Your conversation history is automatically saved to a local **SQLite** database.
- **🔋 Persistent Memory**:
    - **Vector Store**: Document embeddings are stored persistently using **Chroma** (`./chroma_db`), so you don't need to re-process files every time.
    - **Chat History**: ensuring your conversations are always available (`./data/chat_history.db`).

## Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **LLM Engine**: [LangChain](https://www.langchain.com/) + OpenAI GPT-4o
- **Vector Database**: [ChromaDB](https://www.trychroma.com/)
- **Application Database**: SQLite (for sessions and history)

## Setup & Installation

1.  **Clone the Repository** (if applicable)

2.  **Install Dependencies**
    Ensure you have Python 3.10+ installed.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Create a `.env` file in the root directory and add your OpenAI API key:
    ```env
    OPENAI_API_KEY=your_sk_project_api_key_here
    ```

4.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

## Usage Guide

1.  **Upload Documents**: Use the sidebar to upload one or more PDF files. Wait for the "Processed!" confirmation.
2.  **Start Chatting**: Type your question in the chat input. The AI will answer based on the uploaded documents.
3.  **Manage Sessions**: Use the "New Chat" button to start a fresh topic. Switch between existing sessions using the sidebar list.
4.  **View Sources**: Expand the "Sources" dropdown under each AI response to see exactly which parts of the documents were used.

## Project Structure

- `app.py`: Main Streamlit application entry point.
- `modules/rag_engine.py`: Core logic for PDF loading, splitting, embedding, and RAG chain creation.
- `modules/db_manager.py`: Database operations for managing chat sessions and history (SQLite).
- `data/`: Stores local database files.
- `chroma_db/`: Stores vector embeddings.
