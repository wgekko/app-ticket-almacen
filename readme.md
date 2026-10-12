# 🛒 Punto de Venta & Gestión - Almacén Don Pepe

Una aplicación web interactiva y modular desarrollada en **Python** y **Streamlit** diseñada para optimizar las operaciones de cobro, gestión de inventario y análisis financiero de pequeños y medianos comercios de barrio.

---

## 🚀 Características Principales

- **🛍️ Punto de Venta (POS) Inteligente:**
  - Integración para lectura rápida mediante escáner USB de **códigos de barras**.
  - Cálculo automático de tributos (**IVA 21%** e **Ingresos Brutos** ajustados por provincia).
  - Soporte para múltiples medios de pago: *Efectivo, Tarjeta de Débito, Tarjeta de Crédito, Transferencia / QR*.
  - Generación instantánea de tickets en **PDF** optimizados para impresión en comanderas de 80mm.

- **📦 Gestión de Productos (CRUD Completo):**
  - Alta, modificación, actualización de stock y eliminación de productos.
  - Generación y vinculación de códigos de barra únicos por artículo.

- **📂 Carga Masiva desde Excel:**
  - Importación masiva de catálogos mediante archivos `.xlsx` o `.xls` con mapeo dinámico de columnas.

- **📊 Panel Estadístico Financiero:**
  - Métricas en tiempo real de recaudación y cantidad de ventas.
  - Gráficos interactivos de ingresos diarios, ventas por medio de pago y ranking de productos más vendidos.

- **🔒 Cierre / Arqueo de Caja Diario:**
  - Arqueo de dinero físico en efectivo frente a los registros del sistema.
  - Registro de observaciones, sobrantes y faltantes por turno.

- **📦 Control de Stock y Reposición:**
  - Alertas automáticas para productos con nivel crítico de stock y sugerencias automatizadas de reposición.

---

## 🛠️ Tecnologías Utilizadas

- **Lenguaje:** Python 3.10+
- **Framework Web:** Streamlit
- **Base de Datos:** SQLite3
- **Procesamiento de Datos:** Pandas
- **Generación de Reportes PDF:** FPDF2

---

## 📋 Requisitos Previos e Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/almacen-don-pepe-pos.git
   cd almacen-don-pepe-pos
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install streamlit pandas fpdf2 openpyxl
   ```

4. **Ejecutar la aplicación:**
   ```bash
   streamlit run main.py
   ```

---

## 🎨 Personalización de Estilos (`.streamlit/config.toml`)

Para aplicar el tema visual profesional en modo oscuro, crea el archivo `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#00D1B2"
backgroundColor = "#0F172A"
secondaryBackgroundColor = "#1E293B"
textColor = "#F8FAFC"
font = "sans serif"

[server]
toolbarMode = "minimal"
```