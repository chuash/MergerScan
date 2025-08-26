import re
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain.docstore.document import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# initialise embedding model to be used for RAG
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")


def extract_clean(url):
    """Function to scrape content from provided url, extract the page metadata and clean up the text"""
    loader = WebBaseLoader(
        web_path=url,
        header_template={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        },
    )
    doc = loader.load()
    # Extract metadata from the loaded document object
    metadata = dict(doc[0]).get("metadata")
    # Process and filter the scraped text to get relevant information
    text = dict(doc[0]).get("page_content")
    # Replace tab and nbsp with space, also remove the term 'false' because it just means that specific icon is not showing
    cleaned_text = re.sub(r"\xa0|\t|\r", " ", text).replace("false", "")
    # Remove excess whitespaces
    cleaned_text = (
        re.sub(r" +", " ", cleaned_text)
        .replace(" \n", "\n")
        .replace("\n ", "\n")
        .replace("\n \n", "\n\n")
    )

    return metadata, cleaned_text


if __name__ == "__main__":
    # Step 1: Loading data from external sources (2 from HDB and 1 from CPF)

    HDBurl1 = "https://www.hdb.gov.sg/cs/infoweb/e-resale/resale-purchase-of-an-hdb-resale-flat"
    HDBurl2 = "https://www.hdb.gov.sg/residential/buying-a-flat/understanding-your-eligibility-and-housing-loan-options/flat-and-grant-eligibility/couples-and-families/cpf-housing-grants-for-resale-flats-families"
    CPFurl1 = "https://www.cpf.gov.sg/member/infohub/educational-resources/hdb-option-fee-and-housing-expenses-you-should-know"

    # First HDB url
    metadata_hdb1, cleaned_text_hdb1 = extract_clean(HDBurl1)
    # Remove excess newlines, specific to this HDB website
    cleaned_text_hdb1 = re.sub(r"\n{3,}", "\n\n", cleaned_text_hdb1)
    # Filter for relevant content
    cleaned_text_hdb1 = cleaned_text_hdb1.split("APPLICABLE TO BOTH SELLER AND BUYER\n\n")[1].split("\n\nNOTE:")[0]
    # Create document object with clean text and subsetted metadata
    doc_hdb1 = Document(
        page_content=cleaned_text_hdb1,
        metadata={key: metadata_hdb1[key] for key in ["source", "title", "description"]},
    )

    # First CPF url
    metadata_cpf, cleaned_text_cpf = extract_clean(CPFurl1)
    # Remove excess newlines, specific to this CPF website
    cleaned_text_cpf = re.sub(r"\n{2}", "\n", cleaned_text_cpf)
    cleaned_text_cpf = re.sub(r"\n{3,}", "\n\n", cleaned_text_cpf)
    # Filter for relevant information
    cleaned_text_cpf = cleaned_text_cpf.split("CPF Board\n\n")[1].split("\n\nInformation accurate as of date of publication")[0]
    # Create document object with clean text and subsetted metadata
    doc_cpf = Document(
        page_content=cleaned_text_cpf,
        metadata={key: metadata_cpf[key] for key in ["source", "title", "description"]})

    # Second HDB url
    metadata_hdb2, cleaned_text_hdb2 = extract_clean(HDBurl2)
    # Remove excess newlines, specific to this HDB website
    cleaned_text_hdb2 = re.sub(r"\n{3,}", "\n\n", cleaned_text_hdb2)
    # Filter for relevant information
    cleaned_text_hdb2 = cleaned_text_hdb2.split("CPF Housing Grants for Resale Flats (Families)\n\nCPF Housing Grants for Resale Flats (Families)\n\n")[1].split("\n\nNEXT STEPS")[0]
    # Create document object with clean text and subsetted metadata
    doc_hdb2 = Document(
        page_content=cleaned_text_hdb2,
        metadata={key: metadata_hdb2[key] for key in ["source", "title", "description"]},
    )

    # Combining the Document objects into a list of loaded Documents
    docs = [doc_hdb1, doc_cpf, doc_hdb2]

    # Step 2: split the loaded documents into appropriate chunk length
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,  # set at 20% of chunk size
        add_start_index=True,
        keep_separator=False,
        strip_whitespace=True,
        # length_function= llm.count_tokens,
        # is_separator_regex=True, # if this is true, it can recognise "\. " as period separator, if False, will see this as \. separator
    )

    splitted_documents = text_splitter.split_documents(docs)

    # Step 3: Embedding and storage of chunked documents
    idlist = [
        str(doc.metadata["source"]) + " - " + str(doc.metadata["start_index"])
        for doc in splitted_documents
    ]
    vector_store = Chroma.from_documents(
        collection_name="HDBResale",
        documents=splitted_documents,
        embedding=embeddings_model,
        ids=idlist,
        collection_metadata={"hnsw:space": "cosine"},
        persist_directory="../data/chroma_langchain_db",  # Where to save data locally
    )

    print(f"Number of docs in chromadb: {vector_store._collection.count()}")
    print(f"First doc: {vector_store._collection.peek(limit=1)}")
