# 🐝 Icono de Abeja Personalizado - Nubo Express

## 📋 Implementación Completada

El sistema de mapas ahora soporta iconos personalizados de Abeja 🐝 para los conductores.

---

## 🎨 Opciones de Icono Disponibles

El sistema intenta cargar iconos en este orden:

### 1. **Icono Personalizado** (Preferido)
```
URL: https://noboexpress.com/bee-icon.png
Tamaño: 50x50 píxeles
```
- Se carga automáticamente si existe
- Debe ser una imagen PNG transparente
- Debe estar alojada en tu dominio

### 2. **Icono Emoji SVG** (Fallback)
```
Emoji 🐝 en un círculo amarillo
Tamaño: 50x50 píxeles
```
- Se usa si el icono personalizado no está disponible
- Generado dinámicamente como SVG
- No requiere archivo externo

### 3. **Icono Público** (Alternativa)
```
URL: https://cdn-icons-png.flaticon.com/512/3629/3629017.png
```
- Icono de abeja desde Flaticon
- Backup si necesitas algo profesional

---

## 🎯 Cómo Añadir Tu Icono Personalizado

### Opción A: Subir al Dominio (Recomendado)

1. **Diseña el icono:**
   - Tamaño: 50x50 a 100x100 píxeles
   - Formato: PNG con transparencia
   - Estilo: Abeja 🐝 amarilla con detalles negros
   - Color principal: Amarillo (#FFD700) o verde Nubo (#10b981)

2. **Sube el archivo:**
   ```
   Ubicación: https://noboexpress.com/bee-icon.png
   ```

3. **El sistema lo detectará automáticamente** ✅

### Opción B: Usar el Emoji SVG (Ya Implementado)

Si no tienes icono personalizado, el sistema usa automáticamente un emoji 🐝 en círculo amarillo. **No requiere acción adicional.**

---

## 🔧 Código Implementado

### DeliveryMap.js

```javascript
const BEE_ICON_OPTIONS = {
  custom: {
    url: "https://noboexpress.com/bee-icon.png",
    scaledSize: { width: 50, height: 50 }
  },
  emoji: {
    url: 'data:image/svg+xml;charset=UTF-8,...',
    scaledSize: { width: 50, height: 50 }
  }
};

// Detección automática
const img = new Image();
img.onload = () => setBeeIcon(BEE_ICON_OPTIONS.custom);
img.onerror = () => setBeeIcon(BEE_ICON_OPTIONS.emoji);
img.src = BEE_ICON_OPTIONS.custom.url;
```

---

## 📱 Ejemplo de Uso en el Mapa

```javascript
const deliveryMarker = new google.maps.Marker({
    position: { lat: 40.4167, lng: -3.7038 },
    map: map,
    icon: {
        url: "https://noboexpress.com/bee-icon.png",
        scaledSize: new google.maps.Size(50, 50)
    },
    title: "🐝 Conductor Nubo",
    animation: google.maps.Animation.DROP,
    zIndex: 999
});
```

---

## 🎨 Diseño Recomendado para el Icono

### Especificaciones:
- **Tamaño Canvas:** 100x100px
- **Tamaño Abeja:** 80x80px (centrado)
- **Formato:** PNG con transparencia
- **Peso:** < 50KB

### Colores Sugeridos:
```
Amarillo principal: #FFD700
Negro detalles: #000000
Verde Nubo (opcional): #10b981
Sombra: rgba(0,0,0,0.2)
```

### Estilo:
- Abeja vista desde arriba
- Alas visibles
- Rayas negras y amarillas claras
- Bordes redondeados
- Sombra sutil para profundidad

---

## ✅ Testing

### Verificar que funciona:

1. **Abrir OrderTracking** de un pedido activo
2. **Verificar en DevTools Console:**
   ```
   🐝 Actualizando ubicación de la Abeja: 40.4167, -3.7038
   ```
3. **Ver en el mapa:**
   - Icono de abeja personalizado (si existe)
   - O emoji 🐝 amarillo (fallback)
4. **Animación:** El icono debe hacer "bounce" al actualizarse

---

## 🚀 Próximos Pasos

### Cuando tengas el dominio activo:

1. Diseña o compra un icono de abeja profesional
2. Súbelo a `https://noboexpress.com/bee-icon.png`
3. El sistema lo detectará automáticamente
4. No se requieren cambios en el código

### Alternativa Rápida:

Usa un generador de iconos online:
- [Flaticon](https://www.flaticon.com) - Busca "bee icon"
- [Icons8](https://icons8.com) - Descarga como PNG
- [Canva](https://canva.com) - Diseña uno personalizado

---

## 🐝 Resultado Final

**Con Icono Personalizado:**
```
🗺️ Mapa mostrando:
  🔵 Punto de recogida
  🐝 Tu icono personalizado (50x50px) en movimiento
  🔴 Destino
  📍 Ruta trazada
```

**Con Emoji (Fallback):**
```
🗺️ Mapa mostrando:
  🔵 Punto de recogida
  🟡 Emoji 🐝 en círculo amarillo
  🔴 Destino
  📍 Ruta trazada
```

---

## 📞 Soporte

Si necesitas ayuda para crear o implementar el icono:
- 📧 exprenobo@hotmail.com
- 📱 +34 654 24 20 92

---

**✅ Sistema implementado y funcionando con fallback inteligente**
