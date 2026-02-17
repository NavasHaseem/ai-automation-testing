
# frontend/app.py
import os
import sys
import streamlit as st
import requests
from dotenv import load_dotenv, find_dotenv
from pinecone import Pinecone
from io import BytesIO
import openai
import json
import pandas as pd
import tempfile
import re
import urllib
from langchain_openai import ChatOpenAI 
# 1. Get the directory where app.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Navigate up to 'ai-automation-testing' and then into 'Backend'
# app.py is in 'Frontend', so we go up one level to get to the root
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, 'Backend')

# 3. Add to system path
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Add the directory to the system path
from ai_agents.gitrepo_agent import build_analysis_graph
from ai_agents.clonerepo_agent import build_embed_graph
embed_graph = build_embed_graph()
analysis_graph = build_analysis_graph()

load_dotenv(find_dotenv())
BACKEND = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_AUTH_TOKEN", "")  # optional

st.set_page_config(page_title="AI Automation Testing", layout="wide")
st.title("AI Automation Testing")
openai_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(name=os.getenv("PINECONE_INDEX_NAME"))
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Health
try:
    r = requests.get(f"{BACKEND}/health", timeout=5)
    st.success(f"Backend: {r.json().get('status')}")
except Exception as e:
    st.error(f"Backend unreachable: {e}")

st.sidebar.header("Navigation")
section = st.sidebar.radio("Choose Section", ["TestCase Generator", "GitRepo Analysis"], index=1)

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
                        st.dataframe(df, width='stretch')
                        
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
                                    st.dataframe(df, width='stretch')
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
                                                st.dataframe(df, width='stretch')
                                                
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
                                st.dataframe(df,  width='stretch')
                                
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
                            width='stretch',
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

elif section == "TestCase Generator":
   

    st.set_page_config(page_title="AI Testcase Generator", layout="wide")
    st.title("🧪 AI Test Case Generator")
    st.caption("Fetch Jira once → Select → Generate test cases")

    # -------------------------------------------------
    # Session state
    # -------------------------------------------------
 


    if "jira_df" not in st.session_state:
        st.session_state.jira_df = None

    if "selected_jiras" not in st.session_state:
        st.session_state.selected_jiras = []   # List[Dict]

    if "structured_contexts" not in st.session_state:
        st.session_state.structured_contexts = {}  # key -> context

    if "testcases_by_jira" not in st.session_state:
        st.session_state.testcases_by_jira = {}  # key -> list of testcases

    # -------------------------------------------------
    # Step 1: Fetch Jira stories
    # -------------------------------------------------
    st.header("1️⃣ Fetch Jira Stories")

    label = st.text_input(
        "Enter Jira label",
        placeholder="airline, payment, authentication"
    )

    if st.button("Fetch Jira Stories"):
        if not label.strip():
            st.warning("Please enter a label")
        else:
            with st.spinner("Fetching Jira stories..."):
                resp = requests.post( 
                    f"{BACKEND}/fetch-jira",
                    json={"label": label}
                )

            if resp.status_code != 200:
                st.error("Failed to fetch Jira stories")
            else:
                jira_data = resp.json()

                if not jira_data:
                    st.warning("No Jira stories found")
                else:
                    df = pd.DataFrame(jira_data['stories']) 
                    # Normalize columns for UI
                    df["Labels"] = df["Labels"].apply(
                        lambda x: ", ".join(x) if isinstance(x, list) else x
                    )

                    st.session_state.jira_df = df
                    st.success(f"Fetched {len(df)} Jira stories")
 
    # -------------------------------------------------
    # Step 2: Display Jira stories (Multi-select)
    # -------------------------------------------------
    if st.session_state.jira_df is not None:
        st.header("2️⃣ Select Jira Stories")

        # Ensure Select column exists
        if "Select" not in st.session_state.jira_df.columns:
            st.session_state.jira_df.insert(0, "Select", False)

        edited_df = st.data_editor(
            st.session_state.jira_df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select Jira stories to process"
                )
            },
            disabled=[
                col for col in st.session_state.jira_df.columns
                if col != "Select"
            ],
            height=300,
            use_container_width=True
        )

        # Extract selected rows
        selected_rows = edited_df[edited_df["Select"] == True]

        # Build selected_jiras list
        st.session_state.selected_jiras = [
            {
                "key": row["Key"],
                "labels": row["Labels"].split(", "),
                "summary": row["Summary"],
                "description": row["description"]
            }
            for _, row in selected_rows.iterrows()
        ]

        # Preview selected Jira stories
        with st.expander("🔍 Selected Jira Stories (Payload Preview)"):
            if st.session_state.selected_jiras:
                for jira in st.session_state.selected_jiras:
                    st.markdown(f"### {jira['key']}")
                    st.write(jira["summary"])
            else:
                st.info("No Jira stories selected yet.")


    # -------------------------------------------------
    # Step 3: Generate Structured Context (Multi-Jira)
    # -------------------------------------------------
    if st.session_state.selected_jiras:
        st.header("3️⃣ Generate Structured Context")

        if st.button("Generate Context"):
            with st.spinner("Analyzing selected Jira stories..."):

                structured_contexts = {}

                for jira in st.session_state.selected_jiras:
                    resp = requests.post(
                        f"{BACKEND}/generate-context",
                        json={"jira_story": jira}
                    )

                    if resp.status_code == 200:
                        structured_contexts[jira["key"]] = resp.json()[
                            "structured_context"
                        ]
                    else:
                        st.error(
                            f"Failed to generate context for {jira['key']}"
                        )

                if structured_contexts:
                    st.session_state.structured_contexts = structured_contexts
                    st.success(
                        f"Structured Context generated for {len(structured_contexts)} Jira stories"
                    )


    # -------------------------------------------------
    # Step 4: Review Structured Context (Multi-Jira)
    # -------------------------------------------------
    if st.session_state.structured_contexts:
        st.header("4️⃣ Review Structured Context")

        # Select which Jira to review
        selected_ctx_key = st.selectbox(
            "Select Jira story to review",
            list(st.session_state.structured_contexts.keys())
        )

        ctx = st.session_state.structured_contexts[selected_ctx_key]

        # ----------------------------
        # Story Intent
        # ----------------------------
        st.subheader("🎯 Story Intent")
        st.write(ctx["story_intent"]["summary"])

        # ----------------------------
        # Story Goal
        # ----------------------------
        st.subheader("🏁 Story Goal")
        st.write(ctx["story_goal"]["goal_statement"])

        if ctx["story_goal"]["success_conditions"]:
            st.markdown("**Success Conditions:**")
            for cond in ctx["story_goal"]["success_conditions"]:
                st.markdown(f"- {cond}")


        
        # ----------------------------
        # In-Scope Systems
        # ----------------------------
        st.subheader("🧩 In-Scope Systems")

        for system in ctx["in_scope_systems"]:
            with st.expander(system["system_name"]):
                st.markdown(f"**Type:** {system['system_type']}")
                st.markdown(f"**Responsibility:** {system['responsibility']}")

        # ----------------------------
        # Testable Behaviors
        # ----------------------------
        st.subheader("🧪 Testable Behaviors")

        for behavior in ctx["testable_behaviors"]:
            with st.expander(
                f"[{behavior['behavior_intent']}] {behavior['behavior_description']}"
            ):
                st.markdown(f"**Derived From:** {behavior['derived_from']}")
                st.markdown(
                    f"**Observable Outcome:** {behavior['observable_outcome']}"
                )

        # ----------------------------
        # Constraints & Rules
        # ----------------------------
        if ctx["constraints_and_rules"]:
            st.subheader("⚠️ Constraints & Rules")

            for rule in ctx["constraints_and_rules"]:
                with st.expander(rule["rule"]):
                    st.markdown(f"**Rule Type:** {rule['rule_type']}")
                    st.markdown(
                        f"**Derived From:** {rule['derived_from']}"
                    )


        
        # ----------------------------
        # Grounding Statement
        # ----------------------------
        with st.expander("📌 Grounding Statement"):
            st.write(ctx["grounding_statement"])



    # -------------------------------------------------
    # Step 5: Generate Test Cases (Multi-Jira)
    # -------------------------------------------------
    if st.session_state.structured_contexts:
        st.header("5️⃣ Generate Test Cases")

        if st.button("Generate Test Cases"):
            with st.spinner("Generating test cases for selected Jira stories..."):

                for jira in st.session_state.selected_jiras:
                    jira_key = jira["key"]

                    structured_context = st.session_state.structured_contexts.get(jira_key)
                    if not structured_context:
                        continue  # safety guard

                    resp = requests.post(
                        f"{BACKEND}/generate-testcases",
                        json={
                            "jira_story": jira,
                            "structured_context": structured_context
                        }
                    )

                    if resp.status_code == 200:
                        st.session_state.testcases_by_jira[jira_key] = resp.json()["testcases"]
                    else:
                        st.error(f"Failed to generate test cases for {jira_key}")

            st.success("Test case generation completed")
    # -------------------------------------------------
    # Step 6: Review Generated Test Cases
    # -------------------------------------------------
    if st.session_state.testcases_by_jira:
        st.header("6️⃣ Review Generated Test Cases")

        jira_key_to_view = st.selectbox(
            "Select Jira story to view test cases",
            list(st.session_state.testcases_by_jira.keys())
        )

        testcases = st.session_state.testcases_by_jira.get(jira_key_to_view, [])

        if testcases:
            st.subheader(f"🧪 Test Cases for {jira_key_to_view}")

            df = pd.DataFrame(testcases)

            st.dataframe(
                df,
                use_container_width=True,
                height=400
            )


            # 2. Function to convert DataFrame to Excel (using BytesIO)
            # The function is cached to run efficiently on subsequent app reruns
            @st.cache_data
            def convert_df_to_excel(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    writer.close() # Close the writer to save the file to the BytesIO object
                processed_data = output.getvalue()
                return processed_data

            excel_data = convert_df_to_excel(df)

            st.download_button(
                    label="📥 Download Excel file",
                    data=excel_data,
                    file_name='data_download.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    help="Click to download the current data as an XLSX file"
                )
        else:
            st.info("No test cases available for this Jira story.")

elif section == "GitRepo Analysis":
    st.header("📂 GitRepo Analysis")
    st.info("Enter a GitHub repository URL to analyze its README file and extract insights")
    
    tab1, tab2 = st.tabs(["GitRepo Analysis", " Test case generation"])

# =============================
# TAB 1 — GITHUB README ANALYSIS
# =============================
    with tab1:
        st.header("📖 GitRepo Analysis")
        
        # GitHub URL Input
        repo_url = st.text_input("🔗 Enter GitHub Repository URL", placeholder="https://github.com/user/repo")
        
        # Analyze Button
        if st.button("▶️ Analyze", type="primary", use_container_width=True, key="analyze_readme"):
            
            if not repo_url:
                st.warning("Please enter a GitHub repository URL")
            else:
                with st.spinner("Analyzing README from repository..."):
                    
                    result = embed_graph.invoke({
                        "repo_url": repo_url
                    }) 


                    st.success("Analysis completed! ✅")

                    if "readme_context" in result:
                        with st.expander("📄 README Context", expanded=True):
                            st.text(result["readme_context"])
                    
                    if "embedding_status" in result:
                        st.info(result["embedding_status"])

                    
    # =============================
    # TAB 2 — EXCEL BASED PROJECT ANALYSIS
    # =============================
    with tab2:
        st.header("📊 Excel Based Project Analysis")

        uploaded_excel = st.file_uploader(
            "📄 Upload Excel File",
            type=["xlsx"]
        )

        if st.button("Run Analysis", type="primary", use_container_width=True, key="analyze_excel"):

            if not uploaded_excel:
                st.warning("Please upload an Excel file first")
            else:
                with st.spinner("Running analysis workflow..."):

                    try:

                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=".xlsx"
                        ) as tmp_file:
                            tmp_file.write(uploaded_excel.read())
                            excel_path = tmp_file.name

                        result = analysis_graph.invoke({
                            "pinecone_index": index,
                            "openai_client": client,
                            "llm": llm,
                            "excel_path": excel_path
                        })

                        st.success("Project analysis completed successfully ")

                        if "generated_responses" in result and result["generated_responses"]:
                            st.subheader("Generated Test Cases")
                            for idx, response in enumerate(result["generated_responses"], 1):
                                with st.expander(f"Test Case {idx}"):
                                    st.code(response, language="java")

                        os.remove(excel_path)

                    except Exception as e:
                        st.error(f"Analysis Failed: {str(e)}")

     
