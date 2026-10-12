from datetime import datetime
import io
import pandas as pd
import sqlite3
import streamlit as st
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_NAME = "almacen.db"


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  # Tabla de productos (CRUD con Código de Barras)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            codigo_barras TEXT UNIQUE
        )
    """)

  # Tabla de ventas registradas (con Medio de Pago)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            provincia TEXT NOT NULL,
            neto REAL NOT NULL,
            iva REAL NOT NULL,
            iibb REAL NOT NULL,
            total REAL NOT NULL,
            medio_pago TEXT NOT NULL
        )
    """)

  # Tabla de detalle de items vendidos
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            producto_nombre TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            subtotal REAL,
            fecha TEXT,
            FOREIGN KEY(venta_id) REFERENCES ventas(id)
        )
    """)

  # Tabla para Arqueos / Cierres de Caja
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS arqueo_caja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            monto_sistema REAL NOT NULL,
            monto_declarado REAL NOT NULL,
            diferencia REAL NOT NULL,
            observaciones TEXT
        )
    """)

  # Insertar productos iniciales si la tabla está vacía
  cursor.execute("SELECT COUNT(*) FROM productos")
  if cursor.fetchone()[0] == 0:
    productos_iniciales = [
        ("Pan amasado (kg)", 2057.85, 50, "7790010001"),
        ("Leche entera 1L", 983.47, 40, "7790010002"),
        ("Huevos x12", 3297.52, 30, "7790010003"),
        ("Arroz 1kg", 1314.05, 40, "7790010004"),
        ("Aceite 1L", 2223.14, 25, "7790010005"),
        ("Azúcar 1kg", 1561.98, 35, "7790010006"),
        ("Café 170g", 4123.97, 20, "7790010007"),
        ("Té x100", 1809.92, 30, "7790010008"),
        ("Fideos 400g", 818.18, 50, "7790010009"),
        ("Atún lata", 1561.98, 40, "7790010010"),
        ("Bebida 3L", 2140.50, 20, "7790010011"),
        ("Detergente 3L", 5776.86, 15, "7790010012"),
    ]
    cursor.executemany(
        """
            INSERT INTO productos (nombre, precio, stock, codigo_barras) 
            VALUES (?, ?, ?, ?)
        """,
        productos_iniciales,
    )
  conn.commit()
  conn.close()


init_db()

# --- TASAS DE INGRESOS BRUTOS POR PROVINCIA (%) ---
IMPUESTOS_IIBB = {
    "Buenos Aires": 3.5,
    "CABA": 3.0,
    "Córdoba": 4.0,
    "Santa Fe": 3.5,
    "Mendoza": 3.0,
    "Tucumán": 4.5,
    "Entre Ríos": 3.0,
    "Salta": 3.6,
    "Misiones": 4.5,
    "Chaco": 3.5,
    "Corrientes": 3.0,
    "Santiago del Estero": 3.0,
    "San Juan": 3.0,
    "Jujuy": 3.0,
    "Río Negro": 3.0,
    "Neuquén": 3.0,
    "Formosa": 3.0,
    "Chubut": 3.0,
    "San Luis": 3.0,
    "Catamarca": 3.0,
    "La Pampa": 3.0,
    "La Rioja": 2.5,
    "Santa Cruz": 3.0,
    "Tierra del Fuego": 2.0,
}

# --- CONFIGURACIÓN DE LA INTERFAZ STREAMLIT ---
st.set_page_config(
    page_title="Punto de Venta - Almacén Don Pepe", layout="wide"
)

st.header("🛒 Punto de Venta & Gestión - Almacén Don Pepe")

# Menú lateral ampliado
menu = st.sidebar.selectbox(
    "Menú Principal",
    [
        "Punto de Venta (POS)",
        "Gestión de Productos (CRUD)",
        "Carga Masiva (Excel)",
        "Estadísticas de Ventas",
        "Control de Stock y Reposición",
        "Cierre / Arqueo de Caja",
    ],
)

# Inicializar carrito en la sesión
if "carrito" not in st.session_state:
  st.session_state.carrito = {}

# --- 1. MÓDULO PUNTO DE VENTA (POS) ---
if menu == "Punto de Venta (POS)":
  st.subheader(":material/box_add: Caja Registradora")

  col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
  with col_p1:
    provincia_seleccionada = st.selectbox(
        "Provincia (Ingresos Brutos):", list(IMPUESTOS_IIBB.keys())
    )
  with col_p2:
    tasa_iibb = IMPUESTOS_IIBB[provincia_seleccionada]
    st.info(f"Tasa IIBB ({provincia_seleccionada}): **{tasa_iibb}%**")
  with col_p3:
    medio_pago = st.selectbox(
        "Medio de Pago:",
        ["Efectivo", "Tarjeta Débito", "Tarjeta Crédito", "Transferencia / QR"],
    )

  conn = sqlite3.connect(DB_NAME)
  productos_df = pd.read_sql_query("SELECT * FROM productos", conn)
  conn.close()

  # Input para Escáner de Código de Barras o Búsqueda
  busqueda = st.text_input(
      ":material/barcode_scanner: Escanear código de barras o buscar producto...", key="input_busqueda"
  )

  # Si escanean un código de barra exacto, agregarlo de inmediato
  if busqueda:
    match_bc = productos_df[
        productos_df["codigo_barras"].astype(str) == busqueda.strip()
    ]
    if not match_bc.empty:
      p_id = match_bc.iloc[0]["id"]
      p_nom = match_bc.iloc[0]["nombre"]
      p_pre = match_bc.iloc[0]["precio"]
      p_stock = match_bc.iloc[0]["stock"]

      if p_stock > 0:
        if p_id in st.session_state.carrito:
          if st.session_state.carrito[p_id]["cantidad"] < p_stock:
            st.session_state.carrito[p_id]["cantidad"] += 1
          else:
            st.warning(f"Stock máximo alcanzado para {p_nom}")
        else:
          st.session_state.carrito[p_id] = {
              "nombre": p_nom,
              "precio": p_pre,
              "cantidad": 1,
          }
        st.success(f"Agregado: {p_nom}")
        st.rerun()
    else:
      # Filtrar catálogo normal por texto
      productos_df = productos_df[
          productos_df["nombre"].str.contains(busqueda, case=False, na=False)
      ]

  col_catalogo, col_carrito = st.columns([3, 2])

  with col_catalogo:
    st.markdown("### :material/library_books: Catálogo Rápido")
    cols = st.columns(3)
    for index, row in productos_df.iterrows():
      with cols[index % 3]:
        stock_disp = row["stock"]
        btn_label = f"{row['nombre']}\n${row['precio']:,.0f}\n(Stock: {stock_disp})"
        if st.button(
            btn_label,
            key=f"prod_{row['id']}",
            width='stretch',
            disabled=(stock_disp <= 0),
        ):
          prod_id = row["id"]
          if prod_id in st.session_state.carrito:
            if st.session_state.carrito[prod_id]["cantidad"] < stock_disp:
              st.session_state.carrito[prod_id]["cantidad"] += 1
            else:
              st.warning("No hay más stock disponible.")
          else:
            st.session_state.carrito[prod_id] = {
                "nombre": row["nombre"],
                "precio": row["precio"],
                "cantidad": 1,
            }
          st.rerun()

  with col_carrito:
    st.markdown("### :material/shopping_cart: Venta Actual (Carrito)")

    if not st.session_state.carrito:
      st.warning(":material/shopping_cart: El carrito está vacío.")
    else:
      neto = 0
      items_a_borrar = []
      for prod_id, item in st.session_state.carrito.items():
        subtotal = item["precio"] * item["cantidad"]
        neto += subtotal

        c1, c2, c3 = st.columns([3, 2, 1])
        c1.text(f"{item['nombre']}")
        c2.text(f"x{item['cantidad']} (${subtotal:,.0f})")
        if c3.button("🗑️", key=f"del_{prod_id}"):
          items_a_borrar.append(prod_id)

      for pid in items_a_borrar:
        del st.session_state.carrito[pid]
        st.rerun()

      st.markdown("---")
      iva = neto * 0.21
      iibb = neto * (tasa_iibb / 100)
      total = neto + iva + iibb

      st.text(f"Neto: ${neto:,.2f}")
      st.text(f"IVA (21%): ${iva:,.2f}")
      st.text(f"IIBB ({provincia_seleccionada} {tasa_iibb}%): ${iibb:,.2f}")
      st.markdown(f"### Total: ${total:,.2f}")
      st.caption(f":material/payments: Pago vía: **{medio_pago}**")

      if st.button(":material/credit_card: Cobrar y Generar Ticket", width='stretch'):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Registrar Venta principal con medio de pago
        cursor.execute(
            """
                    INSERT INTO ventas (fecha, provincia, neto, iva, iibb, total, medio_pago)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
            (
                fecha_actual,
                provincia_seleccionada,
                neto,
                iva,
                iibb,
                total,
                medio_pago,
            ),
        )
        venta_id = cursor.lastrowid

        # Registrar detalles y descontar stock
        for prod_id, item in st.session_state.carrito.items():
          sub = item["precio"] * item["cantidad"]
          cursor.execute(
              """
                        INSERT INTO detalle_ventas (venta_id, producto_nombre, cantidad, precio_unitario, subtotal, fecha)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
              (
                  venta_id,
                  item["nombre"],
                  item["cantidad"],
                  item["precio"],
                  sub,
                  fecha_actual,
              ),
          )
          cursor.execute(
              """
                        UPDATE productos SET stock = stock - ? WHERE id = ?
                    """,
              (item["cantidad"], prod_id),
          )

        conn.commit()
        conn.close()

        # Generar PDF del Ticket
        pdf = FPDF(unit="mm", format=(80, 160))
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "ALMACEN DON PEPE", 0, 1, "C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, f"Fecha: {fecha_actual}", 0, 1, "C")
        pdf.cell(0, 5, f"Provincia: {provincia_seleccionada}", 0, 1, "C")
        pdf.cell(0, 5, f"Pago: {medio_pago}", 0, 1, "C")
        pdf.cell(0, 5, "-" * 38, 0, 1, "C")

        pdf.set_font("Arial", "B", 9)
        pdf.cell(35, 5, "Producto", 0, 0, "L")
        pdf.cell(12, 5, "Cant", 0, 0, "C")
        pdf.cell(18, 5, "Total", 0, 1, "R")
        pdf.set_font("Arial", "", 9)

        for item in st.session_state.carrito.values():
          sub = item["precio"] * item["cantidad"]
          pdf.cell(35, 5, item["nombre"][:18], 0, 0, "L")
          pdf.cell(12, 5, str(item["cantidad"]), 0, 0, "C")
          pdf.cell(18, 5, f"${sub:,.0f}", 0, 1, "R")

        pdf.cell(0, 5, "-" * 38, 0, 1, "C")
        pdf.cell(45, 5, "Neto:", 0, 0, "R")
        pdf.cell(20, 5, f"${neto:,.2f}", 0, 1, "R")
        pdf.cell(45, 5, "IVA (21%):", 0, 0, "R")
        pdf.cell(20, 5, f"${iva:,.2f}", 0, 1, "R")
        pdf.cell(45, 5, f"IIBB ({tasa_iibb}%):", 0, 0, "R")
        pdf.cell(20, 5, f"${iibb:,.2f}", 0, 1, "R")
        pdf.set_font("Arial", "B", 10)
        pdf.cell(45, 6, "TOTAL:", 0, 0, "R")
        pdf.cell(20, 6, f"${total:,.2f}", 0, 1, "R")

        # Compatibilidad de bytes para Streamlit download_button
        raw_pdf = pdf.output()
        pdf_output = (
            bytes(raw_pdf)
            if isinstance(raw_pdf, bytearray)
            else raw_pdf.encode("latin1")
        )

        st.success("¡Venta cobrada con éxito!")
        st.download_button(
            label=":material/list_alt_check: Descargar Ticket en PDF",
            data=pdf_output,
            file_name=f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
        )
        st.session_state.carrito = {}


# --- 2. MÓDULO GESTIÓN DE PRODUCTOS (CRUD) ---
elif menu == "Gestión de Productos (CRUD)":
  st.subheader(":material/manage_search: Administración de Productos")
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  tab1, tab2, tab3 = st.tabs(["Agregar", "Modificar", "Eliminar"])

  with tab1:
    with st.form("form_agregar"):
      nombre_nuevo = st.text_input("Nombre del producto")
      precio_nuevo = st.number_input(
          "Precio Neto ($)", min_value=0.0, step=10.0
      )
      stock_nuevo = st.number_input(
          "Stock inicial", min_value=0, step=1, value=10
      )
      cb_nuevo = st.text_input("Código de Barras (Opcional)")
      if st.form_submit_button("Guardar Producto") and nombre_nuevo:
        try:
          cursor.execute(
              """
                        INSERT INTO productos (nombre, precio, stock, codigo_barras) 
                        VALUES (?, ?, ?, ?)
                    """,
              (nombre_nuevo, precio_nuevo, stock_nuevo, cb_nuevo or None),
          )
          conn.commit()
          st.success(f"Producto '{nombre_nuevo}' agregado con éxito.")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error(
              "El código de barras ya existe en otro producto. Verifique."
          )

  with tab2:
    df_prod = pd.read_sql_query("SELECT * FROM productos", conn)
    st.dataframe(df_prod, width='stretch')
    prod_id_mod = st.selectbox(
        "Seleccione ID de Producto", df_prod["id"].tolist()
    )
    if prod_id_mod:
      prod_actual = df_prod[df_prod["id"] == prod_id_mod].iloc[0]
      with st.form("form_modificar"):
        n_nombre = st.text_input("Nombre", value=str(prod_actual["nombre"]))
        n_precio = st.number_input("Precio", value=float(prod_actual["precio"]))
        n_stock = st.number_input("Stock", value=int(prod_actual["stock"]))
        n_cb = st.text_input(
            "Código de Barras",
            value=(
                str(prod_actual["codigo_barras"])
                if prod_actual["codigo_barras"]
                else ""
            ),
        )
        if st.form_submit_button("Actualizar"):
          cursor.execute(
              """
                        UPDATE productos SET nombre = ?, precio = ?, stock = ?, codigo_barras = ? 
                        WHERE id = ?
                    """,
              (n_nombre, n_precio, n_stock, n_cb or None, prod_id_mod),
          )
          conn.commit()
          st.success("Actualizado correctamente.")
          st.rerun()

  with tab3:
    df_prod = pd.read_sql_query("SELECT * FROM productos", conn)
    prod_id_del = st.selectbox(
        "Seleccione Producto a eliminar",
        df_prod["id"].tolist(),
        format_func=lambda x: f"ID {x}: {df_prod[df_prod['id'] == x]['nombre'].values[0]}",
    )
    if st.button("🗑️ Eliminar Producto", type="primary"):
      cursor.execute("DELETE FROM productos WHERE id = ?", (prod_id_del,))
      conn.commit()
      st.success("Producto eliminado.")
      st.rerun()
  conn.close()


# --- 3. MÓDULO CARGA MASIVA (EXCEL) ---
elif menu == "Carga Masiva (Excel)":
  st.subheader(":material/dashboard_2_edit: Cargar Catálogo desde Archivo Excel")
  st.markdown(
      "Sube tu archivo `.xlsx` con columnas para nombre, precio neto y stock."
  )

  archivo_subido = st.file_uploader(
      "Selecciona el archivo Excel", type=["xlsx", "xls"]
  )

  if archivo_subido is not None:
    try:
      # 1. Leer el Excel intentando detectar si los encabezados están en la fila 0 o más abajo
      df_temp = pd.read_excel(archivo_subido)

      # Si la primera columna arranca con Unnamed o NaN, buscaremos la fila de encabezados real (header=2)
      if df_temp.columns[0].startswith("Unnamed") or "ALMACÉN" in str(
          df_temp.columns[0]
      ):
        archivo_subido.seek(0)
        df_excel = pd.read_excel(archivo_subido, header=2)
      else:
        df_excel = df_temp

      # Limpiar filas completamente vacías
      df_excel = df_excel.dropna(how="all")

      st.write("Vista previa de los datos detectados:", df_excel.head())
      cols_disp = df_excel.columns.tolist()

      col1, col2, col3, col4 = st.columns(4)
      with col1:
        idx_nom = (
            cols_disp.index("Nombre del Producto")
            if "Nombre del Producto" in cols_disp
            else 0
        )
        c_nombre = st.selectbox("Columna Nombre", cols_disp, index=idx_nom)

      with col2:
        idx_pre = (
            cols_disp.index("Precio Neto (Sin IVA)")
            if "Precio Neto (Sin IVA)" in cols_disp
            else 0
        )
        c_precio = st.selectbox("Columna Precio Neto", cols_disp, index=idx_pre)

      with col3:
        idx_sto = (
            cols_disp.index("Stock Inicial")
            if "Stock Inicial" in cols_disp
            else 0
        )
        c_stock = st.selectbox("Columna Stock", cols_disp, index=idx_sto)

      with col4:
        c_cb = st.selectbox(
            "Columna Cód. Barras (Opcional)",
            ["Ninguna"] + cols_disp,
            index=0,
        )

      if st.button(
          ":material/upload_file: Importar a Base de Datos", type="primary"
      ):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        contador = 0
        errores = 0

        for _, row in df_excel.iterrows():
          # Validar que el nombre no sea vaciío o nulo
          if pd.isna(row[c_nombre]):
            continue

          nom = str(row[c_nombre]).strip()
          try:
            pre = float(row[c_precio]) if not pd.isna(row[c_precio]) else 0.0
            sto = int(row[c_stock]) if not pd.isna(row[c_stock]) else 0
            cb = (
                str(row[c_cb]).strip()
                if c_cb != "Ninguna" and not pd.isna(row[c_cb])
                else None
            )

            cursor.execute(
                """
                            INSERT INTO productos (nombre, precio, stock, codigo_barras) 
                            VALUES (?, ?, ?, ?)
                        """,
                (nom, pre, sto, cb),
            )
            contador += 1
          except Exception as err:
            errores += 1

        conn.commit()
        conn.close()

        if contador > 0:
          st.success(f"¡Se han importado {contador} productos con éxito!")
          if errores > 0:
            st.warning(
                f"Se omitieron {errores} filas por datos inválidos o códigos de"
                " barra duplicados."
            )
        else:
          st.error(
              "No se pudieron importar productos. Verifique las columnas"
              " seleccionadas."
          )

    except Exception as e:
      st.error(f"Error al leer el archivo Excel: {e}")



# --- 4. MÓDULO ESTADÍSTICAS DE VENTAS ---
elif menu == "Estadísticas de Ventas":
  st.subheader(":material/: Panel de Estadísticas de Ventas")

  conn = sqlite3.connect(DB_NAME)
  ventas_df = pd.read_sql_query("SELECT * FROM ventas", conn)
  detalles_df = pd.read_sql_query("SELECT * FROM detalle_ventas", conn)
  conn.close()

  if ventas_df.empty:
    st.info("Aún no hay ventas registradas.")
  else:
    ventas_df["fecha"] = pd.to_datetime(ventas_df["fecha"])
    ventas_df["Solo_Fecha"] = ventas_df["fecha"].dt.date
    ventas_df["Mes_Ano"] = ventas_df["fecha"].dt.strftime("%Y-%m")

    tot_rec = ventas_df["total"].sum()
    tot_trans = len(ventas_df)

    col1, col2 = st.columns(2)
    col1.metric("Recaudación Total", f"${tot_rec:,.2f}")
    col2.metric("Transacciones Realizadas", f"{tot_trans}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
      st.markdown(":material/point_of_sale: Ventas Diarias")
      v_dia = ventas_df.groupby("Solo_Fecha")["total"].sum().reset_index()
      st.bar_chart(v_dia.set_index("Solo_Fecha"))
    with c2:
      st.markdown(":material/payment_arrow_down: Ventas por Medio de Pago")
      v_pago = ventas_df.groupby("medio_pago")["total"].sum().reset_index()
      st.dataframe(v_pago, width='stretch')

    st.markdown(":material/stacked_inbox: Ventas por Producto")
    if not detalles_df.empty:
      p_stats = (
          detalles_df.groupby("producto_nombre")
          .agg({"cantidad": "sum", "subtotal": "sum"})
          .reset_index()
      )
      p_stats.columns = [
          "Producto",
          "Unidades Vendidas",
          "Recaudación Total ($)",
      ]
      st.dataframe(
          p_stats.sort_values(by="Unidades Vendidas", ascending=False),
          width='stretch',
      )


# --- 5. CONTROL DE STOCK Y REPOSICIÓN ---
elif menu == "Control de Stock y Reposición":
  st.subheader(":material/inventory: Control de Inventario y Alertas")

  conn = sqlite3.connect(DB_NAME)
  df_stock = pd.read_sql_query("SELECT * FROM productos", conn)
  conn.close()

  umbral = st.slider("Umbral de stock bajo", 1, 20, 5)
  stock_bajo = df_stock[df_stock["stock"] <= umbral]

  if not stock_bajo.empty:
    st.warning(f"Hay {len(stock_bajo)} productos con stock crítico.")
    st.dataframe(stock_bajo, width='stretch')
  else:
    st.success("Todo el stock está en niveles óptimos.")

  st.markdown("---")
  st.markdown(":material/shopping_cart_checkout: Sugerencia de Compra (Stock Ideal: 40)")
  df_stock["Sugerencia Compra"] = df_stock["stock"].apply(
      lambda x: max(0, 40 - x)
  )
  st.dataframe(df_stock, width='stretch')


# --- 6. CIERRE / ARQUEO DE CAJA ---
elif menu == "Cierre / Arqueo de Caja":
  st.subheader(":material/paid: Cierre y Arqueo de Caja Diario")

  conn = sqlite3.connect(DB_NAME)
  ventas_df = pd.read_sql_query("SELECT * FROM ventas", conn)
  conn.close()

  fecha_hoy = datetime.now().strftime("%Y-%m-%d")
  st.markdown(f"**Fecha actual:** {fecha_hoy}")

  if not ventas_df.empty:
    ventas_df["Solo_Fecha"] = pd.to_datetime(ventas_df["fecha"]).dt.strftime(
        "%Y-%m-%d"
    )
    ventas_hoy = ventas_df[ventas_df["Solo_Fecha"] == fecha_hoy]
    total_sistema = (
        ventas_hoy[ventas_hoy["medio_pago"] == "Efectivo"]["total"].sum()
        if not ventas_hoy.empty
        else 0.0
    )
  else:
    total_sistema = 0.0

  st.info(
      f"Monto esperado en efectivo según sistema (Efectivo):"
      f" **${total_sistema:,.2f}**"
  )

  with st.form("form_arqueo"):
    efectivo_contado = st.number_input(
        "Dinero contado físicamente en caja ($)",
        min_value=0.0,
        step=100.0,
        value=float(total_sistema),
    )
    observaciones = st.text_area("Observaciones del turno / cierre")
    submit_arqueo = st.form_submit_button("Realizar Cierre de Caja")

    if submit_arqueo:
      diferencia = efectivo_contado - total_sistema
      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO arqueo_caja (fecha, monto_sistema, monto_declarado, diferencia, observaciones)
                VALUES (?, ?, ?, ?, ?)
            """,
          (
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              total_sistema,
              efectivo_contado,
              diferencia,
              observaciones,
          ),
      )
      conn.commit()
      conn.close()

      st.success("¡Arqueo registrado con éxito!")
      if diferencia == 0:
        st.balloons()
        st.success("La caja cierra perfecta ($0 de diferencia).")
      elif diferencia > 0:
        st.warning(f"La caja tiene un SOBRANTE de ${diferencia:,.2f}")
      else:
        st.error(f"La caja tiene un FALTANTE de ${abs(diferencia):,.2f}")