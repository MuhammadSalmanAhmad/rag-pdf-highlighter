```python
from dotenv import load_dotenv
load_dotenv()

```

```python
from google.colab import drive
drive.mount('/content/drive')

```

```python
!pip install langchain-community pypdf

```

```python

from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("benchmarking.pdf")
pages = []
async for page in loader.alazy_load():
    pages.append(page)
    print(page)

```

```python
pages

```

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,
    length_function=len,
    is_separator_regex=False,
)

```

```python
chunks = text_splitter.split_documents(pages)
len(chunks)
print(chunks[0])

```

```python


```

```python
chunks[0].metadata["source"]

```

```python
chunks[0].page_content

```

```python
import fitz  # PyMuPDF
from pathlib import Path
from langchain_core.documents import Document

def highlight_chunks_in_pdf(documents: list[Document]):
    if not documents:
        print("No documents provided. Aborting.")
        return

    pdf_path = documents[0].metadata.get("source")
    if not pdf_path:
        print("No 'source' found in metadata. Aborting.")
        return

    pdf_file = Path(pdf_path)
    output_path = pdf_file.stem + "_highlighted" + pdf_file.suffix

    doc = fitz.open(pdf_path)

    for document in documents:
        page_number = document.metadata.get("page", 0)
        text_to_highlight = document.page_content

        if page_number < 0 or page_number >= len(doc):
            print(f"Page {page_number} does not exist in the PDF. Skipping this chunk.")
            continue

        page = doc[page_number]
        normalized_text = " ".join(text_to_highlight.split())

        matches = page.search_for(normalized_text)

        for match in matches:
            page.add_highlight_annot(match)

    doc.save(output_path)
    doc.close()

    print(f"Highlights saved in '{output_path}'")

```

```python
highlight_chunks_in_pdf(documents=chunks[0:2])

```

<!-- ### Work with a vectorstore this is a


```python
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain import hub

embedding_function = OpenAIEmbeddings()

db = Chroma.from_documents(chunks, embedding_function)
retriever = db.as_retriever(search_kwargs={"k": 15})

```

```python
prompt = hub.pull("rlm/rag-prompt")

llm = ChatOpenAI(model="gpt-4o-mini")


def format_docs(docs):
    return "

".join(doc.page_content for doc in docs)

rag_chain = prompt | llm

```

```python
from typing import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain.schema import Document


class AgentState(TypedDict):
    messages: list[BaseMessage]
    documents: list[Document]

def retrieve(state):
    question = state["messages"][-1].content
    documents = retriever.invoke(question)
    state["documents"] = documents
    return state

def generate_answer(state):
    question = state["messages"][-1].content
    documents = state["documents"]
    generation = rag_chain.invoke({"context": documents, "question": question})
    state["messages"].append(generation)
    return state

```

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

workflow.add_node("retrieve", retrieve)
workflow.add_node("generate_answer", generate_answer)
workflow.add_edge("retrieve", "generate_answer")
workflow.add_edge("generate_answer", END)
workflow.set_entry_point("retrieve")
graph = workflow.compile()

```

```python
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod

display(
    Image(
        graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
    )
)

```

```python
result = graph.invoke(
    input={
        "messages": [HumanMessage(content="What Information do you have about red dragons?")]
    }
)
print(result["messages"])

```

```python
highlight_chunks_in_pdf(result["documents"])

```

```python
from langchain_community.document_loaders import AmazonTextractPDFLoader

loader = AmazonTextractPDFLoader("example_data/alejandro_rosalez_sample-small.jpeg")
documents = loader.load()

```

```python
!pip install boto3 amazon-textract-response-parser

```

```python
!pip install PyMuPDF

``` -->
