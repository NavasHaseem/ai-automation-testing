
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

st.sidebar.header("Navigation")
section = st.sidebar.radio("Choose Section", ["Data Sources", "Jira", "Embed & Upsert", "Query/Test Cases"], index=0)

# =====================================================
# SECTION 1: DATA SOURCES
# =====================================================
if section == "Data Sources":
    st.header("📊 Data Sources")
    st.info("Manage and configure all data sources: Databases, Repositories, and Confluences")
    
    # Sub-tabs for different data source types
    tabs = st.tabs(["Databases", "Repositories", "Confluences"])
    
    # ---- Databases Tab ----
    with tabs[0]:
        st.subheader("🗄️ Databases")
        
        # Database type selector
        db_type = st.selectbox("Database Type", ["MongoDB", "PostgreSQL (DB2 compatible)"])
        
        if db_type == "MongoDB":
            st.markdown("### MongoDB - Document Storage")
            
            # Upload documents
            st.markdown("#### Upload Documents")
            f = st.file_uploader("Select file (.pdf/.docx/.txt)", type=["pdf","docx","txt"], key="mongo_upload")
            tags = st.text_input("Tags (comma-separated)", key="mongo_tags")
            notes = st.text_area("Notes", height=80, key="mongo_notes")

            if f and st.button("Upload to MongoDB", key="mongo_upload_btn"):
                files = {"file": (f.name, f.getvalue(), f.type or "application/octet-stream")}
                data = {"tags": tags, "notes": notes}

                API_TOKEN = os.getenv("API_AUTH_TOKEN", "")
                if API_TOKEN:
                    data["token"] = API_TOKEN

                try:
                    r = requests.post(f"{BACKEND}/files/upload", files=files, data=data, timeout=120)

                    if not r.ok:
                        st.error(f"Upload failed: HTTP {r.status_code}")
                        st.code(r.text)
                    else:
                        try:
                            payload = r.json()
                        except:
                            st.error("Backend returned non-JSON response:")
                            st.code(r.text)
                            st.stop()

                        file_id = payload.get("file_id")
                        if not file_id:
                            st.warning("Upload succeeded, but backend did not return 'file_id'. Full response below:")
                            st.code(json.dumps(payload, indent=2))
                            st.stop()

                        st.success(f"✅ Uploaded! File ID: {file_id}")

                except requests.exceptions.RequestException as e:
                    st.exception(e)
            
            # Browse MongoDB files
            st.markdown("#### Browse Uploaded Files")
            name_contains = st.text_input("Filename contains", key="mongo_name_filter")
            tag_contains = st.text_input("Tag contains", key="mongo_tag_filter")
            limit = st.slider("Limit", 10, 500, 100, 10, key="mongo_limit")
            
            if st.button("List Files", key="mongo_list_btn"):
                try:
                    r = requests.post(f"{BACKEND}/files/list", json={"name_contains": name_contains, "tag_contains": tag_contains, "limit": limit})
                    files = r.json().get("files", [])
                    if files:
                        import pandas as pd
                        df = pd.DataFrame(files)
                        st.dataframe(df, use_container_width=True)
                        
                        # File operations
                        file_id = st.text_input("File ID for operations", key="mongo_file_id")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Download", key="mongo_download_btn"):
                                if not file_id:
                                    st.warning("Enter File ID")
                                else:
                                    url = f"{BACKEND}/files/download/{file_id}"
                                    try:
                                        resp = requests.get(url, headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=60)
                                        if resp.status_code != 200:
                                            st.error(f"Download failed: {resp.status_code} - {resp.text}")
                                        else:
                                            cd = resp.headers.get("Content-Disposition", "")
                                            m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
                                            filename = urllib.parse.unquote(m.group(1)) if m else f"{file_id}"
                                            mime = resp.headers.get("Content-Type", "application/octet-stream")
                                            st.success(f"Ready to save: {filename}")
                                            st.download_button(
                                                label=f"Save {filename}",
                                                data=resp.content,
                                                file_name=filename,
                                                mime=mime,
                                            )
                                    except requests.RequestException as e:
                                        st.error(f"Request error: {e}")
                        
                        with col2:
                            if st.button("Delete", key="mongo_delete_btn"):
                                if not file_id:
                                    st.warning("Enter File ID")
                                else:
                                    try:
                                        r = requests.delete(f"{BACKEND}/files/{file_id}", headers={"Authorization": f"Bearer {API_TOKEN}"})
                                        if r.ok:
                                            st.success(f"✅ Deleted: {file_id}")
                                        else:
                                            st.error(f"Delete failed: {r.status_code}")
                                    except Exception as e:
                                        st.exception(e)
                    else:
                        st.info("No files found")
                except Exception as e:
                    st.exception(e)
        
        elif db_type == "PostgreSQL (DB2 compatible)":
            st.markdown("### PostgreSQL / DB2")
            
            # PostgreSQL tabs
            pg_tabs = st.tabs(["Index to RAG", "Browse Tables", "Custom Query"])
            
            with pg_tabs[0]:
                st.markdown("#### Index PostgreSQL Data into Vector Database")
                st.info("🔄 This indexes database tables into Pinecone for semantic search (RAG layer)")
                
                col1, col2 = st.columns(2)
                with col1:
                    index_option = st.radio("Index Option", ["All Tables", "Specific Table"], key="pg_index_option")
                with col2:
                    namespace = st.text_input("Namespace", value="postgresql-data", key="pg_namespace")
                
                if index_option == "Specific Table":
                    try:
                        r = requests.get(f"{BACKEND}/postgres/tables", headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=10)
                        if r.ok:
                            tables = r.json().get("tables", [])
                            selected_table = st.selectbox("Select Table", tables, key="pg_table_select")
                        else:
                            selected_table = st.text_input("Table Name", key="pg_table_name")
                    except:
                        selected_table = st.text_input("Table Name", key="pg_table_name_fallback")
                else:
                    selected_table = None
                
                chunk_size = st.slider("Rows per Chunk", 1, 20, 5, key="pg_chunk_size")
                limit_per_table = st.number_input("Limit Rows per Table (0 = no limit)", 0, 10000, 0, key="pg_limit")
                
                if st.button("🚀 Index to Vector DB", type="primary", key="pg_index_btn"):
                    with st.spinner("Indexing... This may take a while for large tables"):
                        try:
                            payload = {
                                "namespace": namespace,
                                "chunk_size": chunk_size,
                                "limit_per_table": limit_per_table if limit_per_table > 0 else None
                            }
                            
                            if index_option == "Specific Table" and selected_table:
                                payload["table_name"] = selected_table
                            
                            r = requests.post(
                                f"{BACKEND}/postgres/index",
                                json=payload,
                                headers={"Authorization": f"Bearer {API_TOKEN}"},
                                timeout=300
                            )
                            
                            if r.ok:
                                result = r.json()
                                st.success("✅ Indexing Complete!")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Tables", result.get("tables_processed", 0))
                                with col2:
                                    st.metric("Rows", result.get("total_rows", 0))
                                with col3:
                                    st.metric("Chunks", result.get("total_chunks", 0))
                                with col4:
                                    st.metric("Vectors", result.get("total_vectors", 0))
                                
                                if result.get("table_results"):
                                    st.markdown("#### Detailed Results")
                                    import pandas as pd
                                    df = pd.DataFrame(result["table_results"])
                                    st.dataframe(df, use_container_width=True)
                            else:
                                st.error(f"Indexing failed: HTTP {r.status_code}")
                                st.code(r.text)
                        except Exception as e:
                            st.exception(e)
            
            with pg_tabs[1]:
                st.markdown("#### Browse Tables")
                
                if st.button("Load Tables", key="pg_load_tables_btn"):
                    try:
                        r = requests.get(f"{BACKEND}/postgres/tables", headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=10)
                        
                        if r.ok:
                            res = r.json()
                            tables = res.get("tables", [])
                            
                            if tables:
                                st.success(f"Found {len(tables)} tables")
                                selected_table = st.selectbox("Select a table", tables, key="pg_browse_table")
                                row_limit = st.slider("Row Limit", 10, 500, 100, 10, key="pg_browse_limit")
                                
                                if st.button("Query Table", key="pg_query_table_btn"):
                                    try:
                                        query_r = requests.post(
                                            f"{BACKEND}/postgres/query",
                                            json={"table_name": selected_table, "limit": row_limit},
                                            headers={"Authorization": f"Bearer {API_TOKEN}"},
                                            timeout=30
                                        )
                                        
                                        if query_r.ok:
                                            query_res = query_r.json()
                                            data = query_res.get("data", [])
                                            
                                            if data:
                                                import pandas as pd
                                                df = pd.DataFrame(data)
                                                st.success(f"✅ Retrieved {len(data)} rows")
                                                st.dataframe(df, use_container_width=True)
                                                
                                                csv = df.to_csv(index=False)
                                                st.download_button("Download CSV", csv, f"{selected_table}.csv", "text/csv")
                                            else:
                                                st.info("No data found")
                                        else:
                                            st.error(f"Error: HTTP {query_r.status_code}")
                                            st.code(query_r.text)
                                    except Exception as e:
                                        st.exception(e)
                            else:
                                st.info("No tables found")
                        else:
                            st.error(f"Error: HTTP {r.status_code}")
                            st.code(r.text)
                    except Exception as e:
                        st.exception(e)
            
            with pg_tabs[2]:
                st.markdown("#### Custom SQL Query")
                st.info("⚠️ Only SELECT queries are allowed")
                
                sql_query = st.text_area("Enter SQL Query", value="SELECT * FROM your_table LIMIT 100;", height=150, key="pg_custom_sql")
                
                if st.button("Execute Query", key="pg_execute_btn"):
                    try:
                        r = requests.post(
                            f"{BACKEND}/postgres/query",
                            json={"custom_query": sql_query},
                            headers={"Authorization": f"Bearer {API_TOKEN}"},
                            timeout=30
                        )
                        
                        if r.ok:
                            res = r.json()
                            data = res.get("data", [])
                            
                            if data:
                                import pandas as pd
                                df = pd.DataFrame(data)
                                st.success(f"✅ Query returned {len(data)} rows")
                                st.dataframe(df, use_container_width=True)
                                
                                csv = df.to_csv(index=False)
                                st.download_button("Download Results", csv, "query_results.csv", "text/csv")
                            else:
                                st.info("Query returned no results")
                        else:
                            st.error(f"Error: HTTP {r.status_code}")
                            st.code(r.text)
                    except Exception as e:
                        st.exception(e)
    
    # ---- Repositories Tab ----
    with tabs[1]:
        st.subheader("📦 Repositories")
        st.info("🚧 Coming Soon: GitHub, GitLab, Bitbucket integration")
        st.markdown("""
        **Planned Features:**
        - Connect to GitHub repositories
        - Index code files and documentation
        - Semantic search across codebases
        - Commit history analysis
        """)
    
    # ---- Confluences Tab ----
    with tabs[2]:
        st.subheader("📚 Confluences")
        st.info("🚧 Coming Soon: Atlassian Confluence integration")
        st.markdown("""
        **Planned Features:**
        - Connect to Confluence spaces
        - Index wiki pages and documentation
        - Semantic search across knowledge base
        - Page hierarchy navigation
        """)

# =====================================================
# SECTION 2: JIRA
# =====================================================
elif section == "Jira":
    st.header("🎫 Jira")
    st.info("Browse and manage Jira stories and issues")
    
    max_results = st.slider("Max Results", 10, 200, 100, 10, key="jira_max_results")
    
    if st.button("Fetch Stories", key="jira_fetch_btn"):
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

# =====================================================
# SECTION 3: EMBED & UPSERT
# =====================================================
elif section == "Embed & Upsert":
    st.header("🧠 Embed & Upsert to Vector Database")
    st.info("Process uploaded documents and index them into Pinecone for semantic search")
    
    st.markdown("### Select File to Process")
    file_id = st.text_input("File ID (from MongoDB)", key="embed_file_id")
    
    col1, col2 = st.columns(2)
    with col1:
        chunk_chars = st.slider("Chunk Size (characters)", 500, 3000, 1200, 100, key="embed_chunk_size")
        chunk_overlap = st.slider("Chunk Overlap (characters)", 0, 300, 150, 10, key="embed_overlap")
    with col2:
        namespace = st.selectbox(
            "Target Namespace",
            ["mongodb-files", "postgresql-data", "custom"],
            key="embed_namespace"
        )
        if namespace == "custom":
            namespace = st.text_input("Custom Namespace", value="my-namespace", key="embed_custom_ns")
    
    extra_md = st.text_area("Extra Metadata (JSON)", value="{}", height=100, key="embed_metadata")
    
    if st.button("🚀 Embed & Upsert", type="primary", key="embed_upsert_btn"):
        if not file_id:
            st.warning("Please enter a File ID")
        else:
            try:
                body = {
                    "file_id": file_id,
                    "chunk_chars": int(chunk_chars),
                    "chunk_overlap": int(chunk_overlap),
                    "namespace": namespace,
                    "metadata": json.loads(extra_md or "{}"),
                }

                r = requests.post(
                    f"{BACKEND}/pinecone/embed-upsert",
                    json=body,
                    headers={"Authorization": f"Bearer {API_TOKEN}"},
                    timeout=180
                )
                
                if not r.ok:
                    st.error(f"Error: HTTP {r.status_code}")
                    st.code(r.text)
                else:
                    try:
                        result = r.json()
                        st.success("✅ Successfully embedded and upserted to Pinecone!")
                        
                        # Display metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Vectors Upserted", result.get("vectors_upserted", 0))
                        with col2:
                            st.metric("Model", result.get("model", "N/A"))
                        with col3:
                            st.metric("Dimension", result.get("dimension", 0))
                        
                        # Show LangGraph analysis
                        st.markdown("#### LangGraph Analysis")
                        st.info(f"**Chunk Strategy:** {result.get('chunk_strategy', 'N/A')}")
                        st.text_area("Analysis Details", result.get('analysis', 'N/A'), height=100, key="embed_analysis_display")
                        
                    except Exception as json_err:
                        st.error("Backend returned non-JSON response:")
                        st.code(r.text)
            except json.JSONDecodeError:
                st.error("Invalid JSON in metadata field")
            except Exception as e:
                st.exception(e)

# =====================================================
# SECTION 4: QUERY / TEST CASES
# =====================================================
elif section == "Query/Test Cases":
    st.header("🔍 Query / Test Cases")
    st.info("Search across all indexed data sources using semantic search")
    
    # Query configuration
    st.markdown("### Query Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        search_scope = st.selectbox(
            "Search Scope",
            ["all", "mongodb-files", "postgresql-data"],
            help="'all' searches across documents and PostgreSQL data"
        )
        top_k = st.slider("Top-K Results", 1, 20, 5, key="query_top_k")
    
    with col2:
        filter_json = st.text_area(
            "Filter (JSON)",
            value='{}',
            height=100,
            help="Optional Pinecone filter",
            key="query_filter"
        )
    
    # Query input
    query_text = st.text_area(
        "Your Question",
        placeholder="e.g., What are the main features of the system?",
        height=120,
        key="query_text"
    )
    
    if st.button("🔎 Search", type="primary", key="query_search_btn"):
        if not query_text:
            st.warning("Please enter a question")
        else:
            try:
                body = {
                    "namespace": search_scope,
                    "top_k": top_k,
                    "filter": json.loads(filter_json or "{}"),
                    "text": query_text,
                }
                
                r = requests.post(
                    f"{BACKEND}/pinecone/query",
                    json=body,
                    headers={"Authorization": f"Bearer {API_TOKEN}"},
                    timeout=60
                )
                
                if not r.ok:
                    st.error(f"Error: HTTP {r.status_code}")
                    st.code(r.text)
                else:
                    try:
                        res = r.json()
                        
                        # Display AI-generated answer prominently
                        st.markdown("### 🤖 AI-Generated Answer")
                        answer = res.get("answer", "No answer generated")
                        st.success(answer)
                        
                        # Show PostgreSQL data if available
                        postgres_data = res.get("postgres_data")
                        if postgres_data and postgres_data.get("record_count", 0) > 0:
                            st.markdown("### 📊 Database Context")
                            st.info(f"**Source:** {postgres_data.get('source', 'Unknown')}")
                            st.write(f"**Records Found:** {postgres_data.get('record_count', 0)}")
                            st.caption(postgres_data.get("message", ""))
                        
                        # Show document sources
                        matches = res.get("matches", [])
                        if matches:
                            st.markdown("### 📄 Source Documents")
                            st.caption(f"Found {len(matches)} relevant sources")
                            
                            for i, match in enumerate(matches, 1):
                                source_type = match.get("metadata", {}).get("source", "unknown")
                                score = match.get("score", 0)
                                
                                with st.expander(f"Source {i} - Score: {score:.3f} ({source_type})"):
                                    metadata = match.get("metadata", {})
                                    
                                    # Show metadata
                                    if source_type == "postgresql":
                                        st.write(f"**Table:** {metadata.get('table_name', 'N/A')}")
                                        st.write(f"**Row IDs:** {', '.join(metadata.get('row_ids', []))}")
                                    else:
                                        st.write(f"**Filename:** {metadata.get('filename', 'N/A')}")
                                        st.write(f"**Chunk ID:** {metadata.get('chunk_id', 'N/A')}")
                                    
                                    # Show text content
                                    text = metadata.get("text", "") or metadata.get("text_preview", "")
                                    if text:
                                        st.text_area("Content", text, height=150, key=f"match_text_{i}")
                        else:
                            st.warning("No matching sources found")
                            
                    except Exception as json_err:
                        st.error("Backend returned non-JSON response:")
                        st.code(r.text)
            except json.JSONDecodeError:
                st.error("Invalid JSON in filter field")
            except Exception as e:
                st.exception(e)
                
                if r.ok:
                    res = r.json()
                    data = res.get("data", [])
                    
                    if data:
                        import pandas as pd
                        df = pd.DataFrame(data)
                        st.success(f"✅ Query returned {len(data)} rows")
                        st.dataframe(df, use_container_width=True)
                        
                        # Download option
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "Download Results as CSV",
                            csv,
                            "query_results.csv",
                            "text/csv"
                        )
                    else:
                        st.info("Query returned no results")
                else:
                    st.error(f"Error: HTTP {r.status_code}")
                    st.code(r.text)
            except Exception as e:
                st.exception(e)
