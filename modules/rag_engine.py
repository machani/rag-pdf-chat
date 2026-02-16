import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# from langchain.chains.combine_documents import create_stuff_documents_chain # Removed due to import error
# from langchain_community.vectorstores import Chroma # Removed
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

load_dotenv()

# Initialize Embeddings
embeddings = OpenAIEmbeddings(
    api_key=os.getenv("OPENAI_API_KEY") # Automatically read from env
)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def load_and_split_pdfs(file_paths):
    """Loads multiple PDFs and splits them into chunks."""
    all_docs = []
    for file_path in file_paths:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        all_docs.extend(docs)
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(all_docs)
    return splits

from langchain_chroma import Chroma

def create_vector_store(splits):
    """Creates a persistent Chroma vector store from document splits."""
    if not splits:
        # If no splits, try to load existing DB
        return Chroma(
            persist_directory="./chroma_db", 
            embedding_function=embeddings
        )

    # Create/Update vector store
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    return vectorstore

# from langchain.chains import create_retrieval_chain # Removed due to import error
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

def get_rag_chain(vectorstore):
    """Creates a RAG chain for answering questions."""
    retriever = vectorstore.as_retriever()
    
    system_prompt = (
        "You are an expert technical assistant."
        "Use ONLY the information provided in the context below."
        "Your task is to provide a detailed, well-structured, and explanatory answer."
        "Guidelines:"
        "- Explain concepts step-by-step"
        "- Provide background if needed"
        "- Use bullet points or numbered sections where helpful"
        "- If the answer has multiple aspects, cover all of them"
        "- If the context is insufficient, explicitly say what is missing"
        "Context:"
        "{context}"
        "Answer in a detailed and comprehensive manner.")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # question_answer_chain = create_stuff_documents_chain(llm, prompt) # Removed
    
    
    # Contextualize question prompt
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )
    
    history_aware_retriever = (
        contextualize_q_prompt
        | llm
        | (lambda x: x.content) # Output parser for just content
        | retriever
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Question Answer chain
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )

    # We need to decide whether to use history_aware_retriever or normal retriever
    # This is a bit tricky with simple LCEL. 
    # Let's just always use the rephrasing step if we are supporting history, 
    # but efficiently, we only really need it if history is not empty.
    # For simplicity, we will built the chain to always accept 'chat_history'.

    from langchain_core.runnables import RunnableLambda, RunnableParallel

    rag_chain_with_source = RunnableParallel(
        {
            "context": history_aware_retriever, 
            "chat_history": itemgetter("chat_history"),
            "input": itemgetter("input"),
        }
    ).assign(answer= 
         {
             "context": itemgetter("context") | RunnableLambda(format_docs),
             "chat_history": itemgetter("chat_history"),
             "input": itemgetter("input")
         }
         | qa_prompt 
         | llm
    )
    return rag_chain_with_source

def query_rag(chain, question, history=[]):
    """Queries the RAG chain and returns the answer and sources."""
    response = chain.invoke({"input": question, "chat_history": history})
    
    # response is now a dict with 'context' (docs) and 'answer' (AIMessage)
    answer_text = response["answer"].content if hasattr(response["answer"], "content") else str(response["answer"])
    
    return {
        "answer": answer_text,
        "sources": response["context"]
    }

if __name__ == "__main__":
    # Test block
    print("Running smoke test...")
    docs = [
        Document(page_content="Python is a great programming language.", metadata={"source": "doc1"}),
        Document(page_content="The sky is blue.", metadata={"source": "doc2"}),
    ]
    print("Creating vector store...")
    vectorstore = create_vector_store(docs)
    print("Vector store created. Retrieving...")
    retriever = vectorstore.as_retriever(k=1)
    results = retriever.invoke("programming")
    print(f"Retrieved: {results[0].page_content}")
    assert "Python" in results[0].page_content
    # Smoke test for chain (mocking LLM?)
    # Since we don't have API key, we can't invoke full chain easily.
    # But we verified retriever.
    print("Smoke test passed!")
