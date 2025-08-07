import sqlite3
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from langchain_core.runnables import RunnableSequence
from langchain_core.runnables import RunnableLambda
from langchain_community.document_loaders import SQLDatabaseLoader
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains.sql_database.prompt import PROMPT
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableMap, RunnablePassthrough


# DB setup
conn = sqlite3.connect("employee_database.db", check_same_thread=False)
cursor = conn.cursor()

def get_departments():
    return pd.read_sql("SELECT department_id, department_name FROM departments", conn)

# CRUD Utils
def get_table_data(table):
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def insert_row(table, data):
    placeholders = ", ".join(["?"] * len(data))
    query = f"INSERT INTO {table} VALUES ({placeholders})"
    cursor.execute(query, tuple(data))
    conn.commit()

def update_row(table, key_column, key_value, updates):
    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE {key_column} = ?"
    cursor.execute(query, list(updates.values()) + [key_value])
    conn.commit()

def delete_row(table, key_column, key_value):
    cursor.execute(f"DELETE FROM {table} WHERE {key_column} = ?", (key_value,))
    conn.commit()


def clear_inputs(defaults: dict):
    for key, value in defaults.items():
        if key not in st.session_state or st.session_state[key] != value:
            st.session_state[key] = value


#  Streamlit UI
st.set_page_config(page_title="SmartQueryBot", layout="wide")
tabs = st.tabs(["Employees", "Departments", "Projects", "Chatbot", "Reports"])

# ========== TAB 1: Employees ==========
with tabs[0]:
    st.header("Manage Employees")
    df = get_table_data("employees")
    st.dataframe(df)
    dept_df = get_departments()

    if "clear_flag_emp" in st.session_state and st.session_state["clear_flag_emp"]:
        clear_inputs({
            "add_emp_id": 0,
            "add_emp_name": "",
            "add_e_dept_id": dept_df["department_id"].iloc[0],
            "add_e_salary": 0,
            "upd_emp_id": 0,
            "upd_e_name": "",
            "upd_e_dept_id": dept_df["department_id"].iloc[0],
            "upd_e_salary": 0,
            "del_emp_id": 0
        })
        st.session_state["clear_flag_emp"] = False

    with st.form("add_employee"):
        st.subheader("Add Employee")
        employee_id = st.number_input("ID", step=1, key="add_emp_id")
        name = st.text_input("Name", key="add_emp_name")        
        dept_id = st.selectbox("Department", dept_df["department_id"], key="add_e_dept_id")
        salary = st.number_input("Salary", key="add_e_salary")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            with col1:
                if st.form_submit_button("Add"):
                    insert_row("employees", [employee_id, name, dept_id, salary])
                    st.success("Added!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_emp"] = True
                st.rerun()
        
        
    with st.form("update_employee"):
        st.subheader("Update Employee")
        emp_id = st.number_input("Employee ID to update", step=1, key="upd_emp_id")
        name = st.text_input("New Name", key="upd_e_name")
        dept_id = st.selectbox("New Department", dept_df["department_id"], key="upd_e_dept_id")
        salary = st.number_input("New Salary", key="upd_e_salary")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Update"):
                update_row("employees", "employee_id", emp_id, {
                    "employee_name": name, "department_id": dept_id, "salary": salary
                })
                st.success("Updated!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_emp"] = True
                st.rerun()


    with st.form("delete_employee"):
        st.subheader("Delete Employee")
        emp_id_delete = st.number_input("Delete Employee ID", step=1, key ="del_emp_id")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Delete"):
                delete_row("employees", "employee_id", emp_id_delete)
                st.warning("Deleted!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_emp"] = True
                st.rerun()

# ========== TAB 2: Departments ==========
with tabs[1]:
    st.header("Manage Departments")
    df = get_table_data("departments")
    st.dataframe(df)
    dept_df = get_departments()

    if "clear_flag_dept" in st.session_state and st.session_state["clear_flag_dept"]:
        clear_inputs({
            "add_d_dept_id": 0,
            "add_d_name": "",
            "upd_d_dept_id": dept_df["department_id"].iloc[0],
            "upd_d_name": "",
            "del_dept_id": dept_df["department_id"].iloc[0]
        })
        st.session_state["clear_flag_dept"] = False
    

    with st.form("add_dept"):
        st.subheader("Add Department")
        dept_id = st.number_input("Dept ID", step=1, key="add_d_dept_id")
        name = st.text_input("Dept Name", key="add_d_name")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Add"):
                insert_row("departments", [dept_id, name])
                st.success("Added!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_emp"] = True
                st.rerun()


    with st.form("update_dept"):
        st.subheader("Update Department")
        dept_df = get_departments()       
        dept_id = st.selectbox("Dept ID to update", dept_df["department_id"], key="upd_d_dept_id")
        name = st.text_input("New Name", key="upd_d_name")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Update"):
                update_row("departments", "department_id", dept_id, {"department_name": name})
                st.success("Updated!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_emp"] = True
                st.rerun()

    with st.form("delete_dept"):
        st.subheader("Delete Department")
        del_id = st.selectbox("Delete Dept ID", dept_df["department_id"], key="del_dept_id")  

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:      
            if st.form_submit_button("Delete"):
                delete_row("departments", "department_id", del_id)
                st.warning("Deleted!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_emp"] = True
                st.rerun()

# ========== TAB 3: Projects ==========
with tabs[2]:
    st.header("Manage Projects")
    df = get_table_data("projects")
    st.dataframe(df)
    dept_df = get_departments()
    
    if "clear_flag_proj" in st.session_state and st.session_state["clear_flag_proj"]:
        clear_inputs({
            "add_pid": 0,
            "add_p_name": "",
            "add_p_dept_id": get_departments()["department_id"].iloc[0],
            "add_p_budget": 0,
            "upd_pid": 0,
            "upd_p_name": "",
            "upd_p_dept_id": get_departments()["department_id"].iloc[0],
            "upd_p_budget": 0,
            "del_pid": 0
        })
        st.session_state["clear_flag_proj"] = False

    with st.form("add_proj"):
        st.subheader("Add Project")
        pid = st.number_input("Project ID", step=1, key="add_pid")
        name = st.text_input("Project Name", key="add_p_name")        
        dept_id = st.selectbox("Department", dept_df["department_id"], key="add_p_dept_id")
        budget = st.number_input("Budget", key="add_p_budget")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Add"):
                insert_row("projects", [pid, name, dept_id, budget])
                st.success("Added!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_proj"] = True
                st.rerun()
        

    with st.form("update_proj"):
        st.subheader("Update Project")
        pid = st.number_input("Project ID to update", step=1, key="upd_pid")
        name = st.text_input("New Name", key="upd_p_name")
        dept_id = st.selectbox("New Dept", dept_df["department_id"], key="upd_p_dept_id")
        budget = st.number_input("New Budget", key="upd_p_budget")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Update"):
                update_row("projects", "project_id", pid, {
                    "project_name": name, "department_id": dept_id, "budget": budget
                })
                st.success("Updated!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_proj"] = True
                st.rerun()

    with st.form("delete_proj"):
        st.subheader("Delete Project")
        pid_del = st.number_input("Delete Project ID", step=1, key="del_pid")

        col1, col2 = st.columns([0.1,1], gap="small") #places the buttons side-by-side
        with col1:
            if st.form_submit_button("Delete Project"):
                delete_row("projects", "project_id", pid_del)
                st.warning("Deleted!")
        with col2:
            if st.form_submit_button("Clear"):
                st.session_state["clear_flag_proj"] = True
                st.rerun()



# ========== TAB 4: Chatbot ==========
with tabs[3]:
    st.header("SmartQueryBot 💬")
    st.subheader("🔍 Ask Questions on Your Actual Database")

    # Load once
    if "llm" not in st.session_state:
        st.session_state.llm = Ollama(model="llama3.1")
    if "sql_db" not in st.session_state:
        st.session_state.sql_db = SQLDatabase.from_uri("sqlite:///employee_database.db")

    llm = st.session_state.llm
    db = st.session_state.sql_db

    question = st.text_input("Ask a question like 'List all employees in Marketing'", key="q3")

    if st.button("Ask", key="ask3") and question:
        with st.spinner("Running SQL and formatting..."):
            try:
                # Step 1: LLM generates SQL (grounded by schema)
                sql_chain = db.get_table_info() + f"\n-- Question: {question}\nSELECT"
                query = llm.invoke(sql_chain).split("SELECT", 1)[1]
                full_query = "SELECT " + query.strip().split(";")[0] + ";"

                # Step 2: Execute SQL (real data)
                results = db.run(full_query)

                # Step 3: Format output through LLM (no guessing)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant. Respond ONLY using the provided data."),
                    ("human", "Data:\n{data}\n\nNow answer this: {question}")
                ])
                chain = prompt | llm
                final_answer = chain.invoke({"data": results, "question": question})

                st.success("✅ Answer:")
                st.markdown(f"**{final_answer.strip()}**")

            except Exception as e:
                st.error(f"❌ Error: {e}")


# ========== TAB 5: Reports ==========
with tabs[4]:
    st.subheader("📊 Visualize Data (Employees + Departments + Projects)")

    # Load data with JOINs
    sql_db = SQLDatabase.from_uri("sqlite:///employee_database.db")
    query = """
    SELECT 
        e.employee_id,
        e.employee_name,
        e.salary,
        d.department_id,
        d.department_name,
        p.project_id,
        p.project_name,
        p.budget
    FROM departments d
    LEFT JOIN employees e ON e.department_id = d.department_id
    LEFT JOIN projects p ON p.department_id = d.department_id;
    """
    df_all = pd.read_sql(query, sql_db._engine)

    st.write("🧾 Combined Data Preview:")
    st.dataframe(df_all)

    # Chart Selection
    x_col = st.selectbox("Select X-axis column", df_all.columns)
    y_col = st.selectbox("Select Y-axis column", df_all.columns)
    chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Pie"])

    # Generate Chart
    try:
        st.write("📈 Generated Chart:")
        chart_data = df_all[[x_col, y_col]].dropna()

        if chart_type == "Bar":
            st.bar_chart(chart_data.set_index(x_col))
        elif chart_type == "Line":
            st.line_chart(chart_data.set_index(x_col))
        elif chart_type == "Scatter":
            fig, ax = plt.subplots()
            ax.scatter(chart_data[x_col], chart_data[y_col])
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            st.pyplot(fig)
        elif chart_type == "Pie":
            pie_data = chart_data.groupby(x_col)[y_col].sum()
            fig, ax = plt.subplots()
            ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
            ax.axis("equal")
            st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Chart error: {e}")
