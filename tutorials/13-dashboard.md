# Tutorial 13.5 — Dashboard (Streamlit ou React)

## Opção A — Streamlit (mais rápido, Python)

```bash
uv add streamlit pandas plotly
```

**`dashboard/app.py`** — crie pasta `dashboard/`:
```python
import streamlit as st, httpx, pandas as pd

API="http://localhost:8000"
st.set_page_config(page_title="RaceHub Dashboard", layout="wide")
st.title("🏎️ RaceHub — Estatísticas F1")

# standings
r=httpx.get(f"{API}/standings/drivers")
if r.status_code==200:
    df=pd.DataFrame(r.json())
    st.subheader("Pilotos — Pontos")
    st.bar_chart(df.set_index("first_name")["total_points"] if "total_points" in df else df)
    st.dataframe(df)
else:
    st.warning("API /standings/drivers não disponível, rode Fase 13.1")

# weekend
r2=httpx.get(f"{API}/weekend/next?provider=jolpica")
if r2.status_code==200:
    w=r2.json()
    st.subheader(f"Próxima: {w['race_name']} — {w['circuit_name']}")
    st.json(w)
```

```bash
uv run streamlit run dashboard/app.py --server.port 8501
# abra http://localhost:8501
```

Consome `GET /standings/*` e `GET /weekend/schedule` já existentes.

## Opção B — React (se preferir)

```bash
npx create-react-app frontend
cd frontend
npm install axios recharts
```

**`src/App.jsx`**:
```jsx
import {useEffect,useState} from "react"; import axios from "axios";
export default function App(){
  const [data,setData]=useState([]);
  useEffect(()=>{axios.get("http://localhost:8000/standings/drivers").then(r=>setData(r.data))},[]);
  return <div><h1>RaceHub</h1><pre>{JSON.stringify(data,null,2)}</pre></div>
}
```

```bash
npm start # http://localhost:3000
```

Ambos desacoplados — só consomem `http://localhost:8000/openapi.json`.
