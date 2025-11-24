import os
import asyncio
from dotenv import load_dotenv
import streamlit as st   # type: ignore
from pypdf import PdfReader

from agents import Agent, Runner, function_tool, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

load_dotenv()

API = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

# Function to extract text from PDF (UI use)
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

# Tool exposed to the agent (if agent wants to read from a saved file)
@function_tool
def extract_pdf_text(file_path: str) -> str:
    text = ""
    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

# Agent factory (cached for Streamlit)
@st.cache_resource
def get_agent():
    external_client = AsyncOpenAI(
        api_key=API,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    model = OpenAIChatCompletionsModel(
        model=MODEL,
        openai_client=external_client
    )
    agent = Agent(
        model=model,
        name="StudyNotesAssistant",
        instructions="You are a Study Notes Assistant. First produce a concise summary in bullets, then generate a multiple-choice quiz from the text.",
        tools=[extract_pdf_text],
    )
    return agent

# Streamlit UI (keeps your original layout and buttons)
st.set_page_config(page_title="Study Notes Summarizer & Quiz Generator", layout="wide")
st.title("Study Notes Summarizer & Quiz Generator")

st.sidebar.header("Upload your PDF")
uploaded_files = st.sidebar.file_uploader("Choose one or more PDF files", accept_multiple_files=True, type=["pdf"])

if uploaded_files:
    st.sidebar.success("File(s) uploaded successfully!")
    col1, col2 = st.columns(2)

    # Prepare raw text once
    raw_text = get_pdf_text(uploaded_files)

    with col1:
        st.header("Summary")
        if st.button("Generate Summary"):
            with st.spinner("Generating summary..."):
                agent = get_agent()
                async def run_summary():
                    return await Runner.run(
                        starting_agent=agent,
                        input=f"Summarize this text into concise bullet points:\n\n{raw_text}"
                    )
                result = asyncio.run(run_summary())
                # Runner result may differ; use final_output if available
                output = getattr(result, "final_output", str(result))
                st.write(output)

    with col2:
        st.header("Quiz")
        if st.button("Generate Quiz"):
            with st.spinner("Generating quiz..."):
                agent = get_agent()
                async def run_quiz():
                    return await Runner.run(
                        starting_agent=agent,
                        input=f"Create a 5-question multiple-choice quiz (with 4 options each, mark the correct answer) from the following text:\n\n{raw_text}"
                    )
                result = asyncio.run(run_quiz())
                output = getattr(result, "final_output", str(result))
                st.write(output)