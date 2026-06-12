# 🗺️ Configuración de Google Maps en Nubo

## 📋 Resumen
Google Maps ha sido integrado en tu aplicación Nubo para mostrar:
- **Clientes**: Ubicación del pedido y seguimiento en tiempo real
- **Repartidores**: Ruta óptima desde el negocio hasta el cliente

---

## 🔑 Paso 1: Obtener tu Google Maps API Key

### 1. Accede a Google Cloud Console
Ve a: **https://console.cloud.google.com/**

### 2. Crea un Proyecto (si no tienes uno)
- Haz clic en el menú desplegable de proyectos (arriba izquierda)
- Clic en **"Nuevo Proyecto"**
- Nombre del proyecto: `Nubo Algeciras` (o el que prefieras)
- Clic en **"Crear"**

### 3. Habilita las APIs de Google Maps

#### a) Ve a la Biblioteca de APIs
- En el menú lateral: **"APIs y servicios"** → **"Biblioteca"**

#### b) Habilita las siguientes APIs (busca y habilita cada una):
1. **Maps JavaScript API** ✅ (OBLIGATORIA)
   - Busca: "Maps JavaScript API"
   - Clic en "HABILITAR"

2. **Directions API** ✅ (OBLIGATORIA - para rutas)
   - Busca: "Directions API"
   - Clic en "HABILITAR"

3. **Geocoding API** ✅ (Recomendada - para convertir direcciones en coordenadas)
   - Busca: "Geocoding API"
   - Clic en "HABILITAR"

### 4. Crea las Credenciales (API Key)

#### a) Ve a Credenciales
- En el menú lateral: **"APIs y servicios"** → **"Credenciales"**

#### b) Crear nueva API Key
- Clic en **"+ CREAR CREDENCIALES"**
- Selecciona **"Clave de API"**
- Se generará automáticamente

#### c) Copia tu API Key
```
Ejemplo: AIzaSyBXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx
```
**¡GUÁRDALA EN UN LUGAR SEGURO!**

### 5. (Recomendado) Restringe tu API Key

Para mayor seguridad:

#### a) Restricciones de aplicación
- Clic en el nombre de tu API Key
- En "Restricciones de aplicación", selecciona:
  - **"Referentes HTTP (sitios web)"**
- Añade tu dominio:
  ```
  https://delivery-hub-1041.preview.emergentagent.com/*
  localhost:3000/*
  ```

#### b) Restricciones de API
- En "Restricciones de API", selecciona:
  - **"Restringir clave"**
- Marca solo las APIs que habilitaste:
  - ✅ Maps JavaScript API
  - ✅ Directions API
  - ✅ Geocoding API

#### c) Guarda los cambios

---

## 🔧 Paso 2: Configurar la API Key en Nubo

### Opción A: Variable de Entorno (Recomendada)

1. Edita el archivo `/app/frontend/.env`:
```bash
nano /app/frontend/.env
```

2. Reemplaza `YOUR_API_KEY_HERE` con tu API Key real:
```
REACT_APP_GOOGLE_MAPS_API_KEY="AIzaSyBXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx"
```

3. Guarda el archivo (Ctrl + O, Enter, Ctrl + X)

4. Reinicia el frontend:
```bash
sudo supervisorctl restart frontend
```

### Opción B: Configuración Manual

Si prefieres no usar variables de entorno:

1. Edita `/app/frontend/src/components/MapComponent.js`
2. Busca la línea:
```javascript
googleMapsApiKey: process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE'
```
3. Reemplaza `YOUR_API_KEY_HERE` con tu clave

---

## ✅ Paso 3: Verificar la Instalación

1. Abre tu aplicación: https://delivery-hub-1041.preview.emergentagent.com

2. Inicia sesión como **cliente**

3. Crea un pedido y ve al tracking

4. Deberías ver un mapa de Google Maps con:
   - 📍 Marcador azul: Ubicación del negocio
   - 📍 Marcador rojo: Dirección de entrega
   - 🛣️ Ruta trazada (cuando el pedido está en tránsito)

---

## 💰 Costos de Google Maps

### Plan Gratuito de Google
- **$200 USD de crédito gratis cada mes**
- Suficiente para aproximadamente:
  - 28,000 cargas de mapa
  - 40,000 solicitudes de geocodificación
  - 40,000 solicitudes de direcciones

### Para una app pequeña/mediana:
✅ El crédito gratuito es **MÁS QUE SUFICIENTE**

### Facturación:
- Google requiere una tarjeta de crédito
- Solo se cobra si superas los $200/mes de uso
- Puedes configurar alertas y límites

---

## 🛠️ Funcionalidades Implementadas

### Para Clientes:
✅ Ver ubicación del negocio
✅ Ver dirección de entrega
✅ Seguimiento en tiempo real del pedido
✅ Ruta del repartidor (cuando está en camino)

### Para Repartidores:
✅ Ver todas las ubicaciones de entrega
✅ Calcular ruta óptima
✅ Instrucciones de navegación

---

## 🐛 Solución de Problemas

### El mapa no aparece
1. **Verifica la API Key**:
   - ¿La copiaste correctamente?
   - ¿Incluye espacios extra?

2. **Verifica las APIs habilitadas**:
   - Maps JavaScript API debe estar habilitada
   - Directions API debe estar habilitada

3. **Revisa la consola del navegador** (F12):
   - Busca errores de Google Maps
   - Si dice "API Key inválida": revisa el paso 1

### Mensaje: "For development purposes only"
- Esto aparece si NO has configurado la facturación
- La API Key funciona, pero tiene marca de agua
- Solución: Configura facturación en Google Cloud

### Error: "This API project is not authorized"
- Necesitas habilitar "Maps JavaScript API"
- Ve a Google Cloud Console → Biblioteca → Habilita la API

---

## 📞 Soporte Adicional

Si tienes problemas:
1. Revisa los logs del frontend:
   ```bash
   tail -f /var/log/supervisor/frontend.*.log
   ```

2. Revisa la consola del navegador (F12)

3. Verifica que tu API Key esté activa en:
   https://console.cloud.google.com/apis/credentials

---

## 🎉 ¡Listo!

Una vez configurada tu API Key, los mapas funcionarán perfectamente en:
- Página de tracking de pedidos
- Dashboard de repartidores
- Cualquier vista que muestre ubicaciones

**¡Disfruta de Google Maps en Nubo!** 🗺️✨
