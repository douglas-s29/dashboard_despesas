
import streamlit as st
import pandas as pd
import sqlite3
import re
import plotly.express as px

DB_PATH = "database/financeiro.db"

st.set_page_config(page_title="Dashboard de Despesas", layout="wide")

# ----------------------
# Helpers
# ----------------------
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        data TEXT,
        descricao TEXT,
        valor REAL,
        banco TEXT,
        categoria TEXT,
        status TEXT,
        parcelas TEXT,
        ano INTEGER,
        mes INTEGER
    )
    """)
    conn.commit()
    conn.close()

def replace_db(df):
    conn = get_conn()
    conn.execute("DROP TABLE IF EXISTS despesas")
    conn.execute("""
    CREATE TABLE despesas (
        data TEXT,
        descricao TEXT,
        valor REAL,
        banco TEXT,
        categoria TEXT,
        status TEXT,
        parcelas TEXT,
        ano INTEGER,
        mes INTEGER
    )
    """)
    df.to_sql("despesas", conn, if_exists="append", index=False)
    conn.close()

def load_df():
    conn = get_conn()
    try:
        df = pd.read_sql("SELECT * FROM despesas", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def interpretar_pergunta(texto):
    texto = texto.lower()
    mes = re.search(r"mes\s*(\d{1,2})", texto)
    ano = re.search(r"(20\d{2})", texto)
    categoria = None
    if "assinatura" in texto:
        categoria = "Assinaturas"
    return {
        "mes": int(mes.group(1)) if mes else None,
        "ano": int(ano.group(1)) if ano else None,
        "categoria": categoria
    }

def responder_pergunta(df, filtros):
    q = df.copy()
    if filtros["mes"]:
        q = q[q["mes"] == filtros["mes"]]
    if filtros["ano"]:
        q = q[q["ano"] == filtros["ano"]]
    if filtros["categoria"]:
        q = q[q["categoria"].str.contains(filtros["categoria"], case=False, na=False)]
    return q["valor"].sum()

# ----------------------
# UI
# ----------------------
st.title("💸 Dashboard de Despesas")

st.markdown("### 📥 Upload da base (CSV ou XLSX)")
uploaded = st.file_uploader(
    "Envie o arquivo no modelo padrão. O upload SUBSTITUI a base atual.",
    type=["csv", "xlsx"]
)

init_db()

if uploaded:
    if uploaded.name.endswith(".csv"):
        df_up = pd.read_csv(uploaded)
    else:
        df_up = pd.read_excel(uploaded)

    # normaliza nomes
    df_up.columns = [c.lower().strip() for c in df_up.columns]
    df_up = df_up.rename(columns={"mês": "mes"})

    replace_db(df_up)
    st.success("Base carregada com sucesso! A base anterior foi substituída.")

df = load_df()

st.divider()

# Pergunta
st.markdown("### 💬 Pergunte sobre seus gastos")
pergunta = st.text_input("", placeholder="Quanto gastei no mes 2 de 2025 com assinaturas?")
if pergunta and not df.empty:
    filtros = interpretar_pergunta(pergunta)
    total = responder_pergunta(df, filtros)
    st.success(f"💸 Você gastou R$ {total:,.2f}")
elif pergunta and df.empty:
    st.warning("Carregue uma base primeiro.")

st.divider()

if df.empty:
    st.info("Nenhuma base carregada ainda.")
else:
    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Gasto Total", f"R$ {df.valor.sum():,.2f}")
    col2.metric("📆 Meses", df[['ano','mes']].drop_duplicates().shape[0])
    col3.metric("🧾 Lançamentos", len(df))

    # Evolução mensal
    mensal = df.groupby(["ano","mes"])["valor"].sum().reset_index()
    fig1 = px.bar(mensal, x="mes", y="valor", color="ano", title="Gasto por Mês")
    st.plotly_chart(fig1, use_container_width=True)

    # Categoria
    cat = df.groupby("categoria")["valor"].sum().reset_index()
    fig2 = px.pie(cat, names="categoria", values="valor", hole=0.4, title="Gasto por Categoria")
    st.plotly_chart(fig2, use_container_width=True)

    # Banco
    banco = df.groupby("banco")["valor"].sum().reset_index()
    fig3 = px.bar(banco, x="banco", y="valor", title="Gasto por Banco")
    st.plotly_chart(fig3, use_container_width=True)
