
# frontend/app.py
import os
import urllib
import re
import streamlit as st
import requests
from dotenv import load_dotenv, find_dotenv
import json

load_dotenv(find_dotenv())
BACKEND = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_AUTH_TOKEN", "")  # optional

st.set_page_config(page_title="AI Automation Testing", layout="wide")
st.title("AI Automation Testing")

# Health
try:
    r = requests.get(f"{BACKEND}/health", timeout=5)
    st.success(f"Backend: {r.json().get('status')}")
except Exception as e:
    st.error(f"Backend unreachable: {e}")

st.sidebar.header("Sections")
section = st.sidebar.radio("Choose", ["Upload", "Embed & Upsert &Query", "Jira Stories"], index=0)

# ---- Upload ----
if section == "Upload":
    st.subheader("📁 Upload to MongoDB ")
    f = st.file_uploader("Select file (.pdf/.docx/.txt)", type=["pdf","docx","txt"])
    tags = st.text_input("Tags (comma-separated)")
    notes = st.text_area("Notes", height=80)



    # ... inside section == "Upload"
    if f and st.button("Upload"):
        files = {"file": (f.name, f.getvalue(), f.type or "application/octet-stream")}
        data = {"tags": tags, "notes": notes}

        # If your backend requires a token via form field (as in earlier example):
        API_TOKEN = os.getenv("API_AUTH_TOKEN", "")
        if API_TOKEN:
            data["token"] = API_TOKEN

        try:
            r = requests.post(f"{BACKEND}/files/upload", files=files, data=data, timeout=120)

            # 1) Status check
            if not r.ok:
                # Show status and backend error body
                st.error(f"Upload failed: HTTP {r.status_code}")
                # Try to show JSON error; otherwise raw text
                try:
                    st.error(r.json())
                except Exception:
                    st.error(r.text)
                st.stop()

            # 2) Parse JSON safely
            try:
                payload = r.json()
            except Exception as e:
                st.error("Backend returned non-JSON response.")
                st.code(r.text)
                st.stop()

            # 3) Expect a file_id
            file_id = payload.get("file_id")
            if not file_id:
                st.warning("Upload succeeded, but backend did not return 'file_id'. Full response below:")
                st.code(json.dumps(payload, indent=2))
                st.stop()

            # 4) Success path
            st.success(f"Uploaded file_id: {file_id}")

        except requests.exceptions.RequestException as e:
            st.exception(e)
    st.subheader("📚 Files in MongoDB")
    name_contains = st.text_input("Filename contains")
    tag_contains = st.text_input("Tag contains")
    limit = st.slider("Limit", 10, 500, 100, 10)
    try:
        r = requests.post(f"{BACKEND}/files/list", json={"name_contains": name_contains, "tag_contains": tag_contains, "limit": limit})
        files = r.json().get("files", [])
        if files:
            st.dataframe(files, width="stretch")
            file_id = st.text_input("File ID")
            col1, col2 = st.columns(2)
            with col1:
             if st.button("Download (browser)"):

                 if not file_id:
                     st.warning("Enter File ID")
                 else:
                     url = f"{BACKEND}/files/download/{file_id}"
                     try:

                         resp = requests.get(url, data={"token": API_TOKEN}, timeout=60)


                         if resp.status_code != 200:
                             st.error(f"Download failed: {resp.status_code} - {resp.text}")
                         else:
                             # Parse filename from Content-Disposition
                             cd = resp.headers.get("Content-Disposition", "")
                             m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
                             filename = urllib.parse.unquote(m.group(1)) if m else f"{file_id}"
                             mime = resp.headers.get("Content-Type", "application/octet-stream")

                             st.success(f"Ready to save: {filename}")
                             st.download_button(
                                 label=f"Save {filename}",
                                 data=resp.content,  # bytes from backend
                                 file_name=filename,
                                 mime=mime,
                             )
                     except requests.RequestException as e:
                         st.error(f"Request error: {e}")

            with col2:
                if st.button("Delete"):
                    data = {"token": API_TOKEN} if API_TOKEN else None
                    try:
                        r = requests.delete(f"{BACKEND}/files/{file_id}", data=data)
                        st.success(f"Deleted: {file_id}")
                    except Exception as e:
                        st.exception(e)
        else:
            st.info("No files found.")
    except Exception as e:
        st.exception(e)

# ---- Embed & Upsert ----
elif section ==  "Embed & Upsert &Query":
    st.subheader("🧠 Embed a MongoDB file & upsert to Pinecone")
    file_id = st.text_input("File ID", key="embed_file_id")
    chunk_chars = st.slider("Chunk size (chars)", 500, 3000, 1200, 100)
    chunk_overlap = st.slider("Chunk overlap (chars)", 0, 300, 150, 10)
    namespace = st.text_input("Namespace", "mongodb-files", key="embed_namespace")
    extra_md = st.text_area("Extra metadata (JSON)", value="{}")
    if st.button("Embed & Upsert"):
        try:
            body ={
                "file_id": file_id,
                "chunk_chars": int(chunk_chars),
                "chunk_overlap": int(chunk_overlap),
                "namespace": namespace,
                "metadata": json.loads(extra_md or "{}"),
            }

            if API_TOKEN:
                # since FastAPI expects token via form on upload-only endpoints,
                # here it's JSON; adjust backend if you want token consistently in headers
                token={"token": API_TOKEN}

            print(API_TOKEN)
            r = requests.post(f"{BACKEND}/pinecone/embed-upsert",json=body, headers={"Authorization": f"Bearer {API_TOKEN}"},timeout=180,)
            
            # Check response status
            if not r.ok:
                st.error(f"Error: HTTP {r.status_code}")
                st.code(r.text)
            else:
                try:
                    result = r.json()
                    st.success("✅ Successfully embedded and upserted to Pinecone!")
                    
                    # Display summary in a clean format
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Vectors Upserted", result.get("vectors_upserted", 0))
                    with col2:
                        st.metric("Model", result.get("model", "N/A"))
                    with col3:
                        st.metric("Dimension", result.get("dimension", 0))
                    
                    # Show agent analysis
                    st.info(f"**Chunk Strategy:** {result.get('chunk_strategy', 'N/A')}")
                    st.info(f"**Analysis:** {result.get('analysis', 'N/A')}")
                    
                except Exception as json_err:
                    st.error("Backend returned non-JSON response:")
                    st.code(r.text)
        except Exception as e:
            st.exception(e)

# ---- Query Pinecone ----
    st.subheader("🔎 Query with Jira-first filter, then semantic")
    namespace_query = st.text_input("Namespace", "mongodb-files", key="query_namespace")
    top_k = st.slider("Top-K", 1, 10, 5)
    pinecone_filter = st.text_area("Pinecone filter (JSON)", value='{"source":{"$eq":"mongodb"}}', key="query_filter")
    query_text = st.text_area("Query text (e.g., Jira issue text)")

    if st.button("Search"):
        try:
            body = {
                "namespace": namespace_query,
                "top_k": top_k,
                "filter": __import__("json").loads(pinecone_filter or "{}"),
                "text": query_text,
            }
            r = requests.post(
                f"{BACKEND}/pinecone/query", 
                json=body, 
                headers={"Authorization": f"Bearer {API_TOKEN}"}, 
                timeout=60
            )
            
            # Check response status
            if not r.ok:
                st.error(f"Error: HTTP {r.status_code}")
                st.code(r.text)
            else:
                try:
                    res = r.json()
                    
                    # Display the AI-generated answer prominently
                    answer = res.get("answer", "")
                    if answer:
                        st.success("**Answer:**")
                        st.markdown(f"### {answer}")
                        st.divider()
                    
                    # Show source matches
                    matches = res.get("matches", [])
                    if not matches:
                        st.info("No matches found.")
                    else:
                        st.subheader(f"📚 Source Documents ({len(matches)} matches)")
                        for i, m in enumerate(matches, 1):
                            md = m.get("metadata", {})
                            with st.expander(f"Source {i}: {md.get('filename', 'Unknown')} (Score: {m.get('score', 0):.4f})"):
                                st.markdown(f"**Chunk ID:** {md.get('chunk_id', 'N/A')}")
                                st.markdown(f"**Text Preview:**")
                                st.code(md.get("text_preview", "No preview available"), language="markdown")
                except Exception as json_err:
                    st.error("Backend returned non-JSON response:")
                    st.code(r.text)
        except Exception as e:
            st.exception(e)

# ---- Jira Stories Section ----
elif section == "Jira Stories":
    st.subheader("🎫 Jira Stories")
    
    max_results = st.slider("Max Results", 10, 200, 100, 10)
    
    if st.button("Fetch All Stories"):
        try:
            r = requests.get(
                f"{BACKEND}/jira/stories",
                params={"max_results": max_results},
                headers={"Authorization": f"Bearer {API_TOKEN}"},
                timeout=30
            )
            
            if not r.ok:
                st.error(f"Error: HTTP {r.status_code}")
                st.code(r.text)
            else:
                try:
                    res = r.json()
                    stories = res.get("stories", [])
                    total = res.get("total", 0)
                    
                    st.success(f"✅ Fetched {len(stories)} stories (Total: {total})")
                    
                    # Display stories in a table
                    if stories:
                        import pandas as pd
                        
                        df = pd.DataFrame(stories)
                        st.dataframe(
                            df,
                            use_container_width=True,
                            column_config={
                                "key": "Story Key",
                                "summary": st.column_config.TextColumn("Summary", width="large"),
                                "status": "Status",
                                "issue_type": "Type",
                                "assignee": "Assignee",
                                "priority": "Priority"
                            }
                        )
                        
                        # Show expandable details
                        st.divider()
                        st.subheader("Story Details")
                        for story in stories:
                            with st.expander(f"{story['key']}: {story['summary']}"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Status", story['status'])
                                with col2:
                                    st.metric("Priority", story.get('priority', 'N/A'))
                                with col3:
                                    st.metric("Assignee", story.get('assignee', 'Unassigned'))
                    else:
                        st.info("No stories found")
                        
                except Exception as json_err:
                    st.error("Backend returned non-JSON response:")
                    st.code(r.text)
        except Exception as e:
            st.exception(e)
