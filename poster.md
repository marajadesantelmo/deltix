# 🌊 DELTIX
## El Bot del Humedal - Proyecto de chatbot comuniatrio y colaborativo
Jornadas UNDelta Investiga
---

## 🎯 **CONTEXTO Y PROBLEMÁTICA**

### Región del Delta del Paraná
- **Ubicación**: Delta inferior del Paraná, Buenos Aires, Argentina
- **Características**: numerosas islas habitadas, transporte exclusivamente fluvial
- **Desafíos**: Acceso limitado a información crítica (clima, transporte, servicios)

### Necesidades Identificadas
- ⛈️ **Pronósticos meteorológicos** precisos para navegación segura
- 🚤 **Horarios de transporte público** fluvial actualizado
- 🛒 **Información de servicios** (almaceneras, actividades locales)
- 📱 **Canal de comunicación** accesible sin internet de alta velocidad

---

## 🤖 **SOLUCIÓN TECNOLÓGICA**

### Deltix: Chatbot Multimodal
- **Telegram Bot** (interfaz principal)
- **Aplicación Web** (Streamlit en desarrollo)
- **Integración WhatsApp** (en desarrollo y buscando apoyo financiero)

### Público Objetivo
- 👥 **Residentes permanentes** 
- 🚤 **Navegantes recreativos** y turistas
- 🏪 **Comerciantes locales** y prestadores de servicios
- 🚨 **Servicios de emergencia** y transporte

---

## 🔧 **ARQUITECTURA TÉCNICA**

### Stack Tecnológico
```
├── Backend: Python + Telegram Bot API
├── Base de datos: MySQL (conversaciones)
├── Web Scraping: Selenium + BeautifulSoup
├── IA: DeepSeek LLM via OpenRouter
├── Frontend web: Streamlit
└── Deployment: PythonAnywhere + GitHub Actions
```

### Fuentes de Datos (Web Scraping)
- 🌊 **INA** (Instituto Nacional del Agua) - Pronósticos de mareas
- 🌦️ **WindGuru** - Pronósticos meteorológicos marítimos
- ⚓ **Prefectura Naval** - Datos hidrográficos oficiales
- 🚤 **Sitios oficiales** - Horarios de colectivas (transporte público)

### Procesamiento Inteligente
- **RAG (Retrieval-Augmented Generation)**: Base de conocimientos local para respuestas con IA
- **LLM Integration**: Respuestas contextuales con DeepSeek
- **Conversational Memory**: Historial en MySQL para continuidad

---

## 📊 **SERVICIOS IMPLEMENTADOS**

### Información Crítica
- 🌊 **Pronósticos de mareas** (INA + Hidrografía Naval)
- 🌪️ **Pronósticos climáticos** (WindGuru + análisis local)
- ⏰ **Horarios actualizados** de lanchas colectivas

### Servicios Locales
- 🛒 **Directorio de almaceneras** (delivery fluvial)
- 🎯 **Agenda del río** (actividades y emprendimientos)
- 📞 **Contactos de emergencia** y servicios públicos

### Funciones Sociales
- 💬 **Chat inteligente** con IA
- 📧 **Sistema de suscripciones** para alertas diarias
- 🤝 **Canal de colaboración** comunitaria


---

## 🌍 **IMPACTO SOCIAL**

### Beneficios Comunitarios
- ⚡ **Acceso inmediato** a información crítica
- 💰 **Reducción de costos** de comunicación
- 🤝 **Fortalecimiento** del ecosistema local
- 🚨 **Mejora en seguridad** náutica

### Sostenibilidad
- 💚 **Modelo freemium**: Gratis para individuos y proyectos
- 💼 **Suscripciones empresariales** para sustentabilidad
- 🔓 **Código abierto** en GitHub

---

## 🚀 **INNOVACIÓN Y ESCALABILIDAD**

### Características Distintivas
- 🎯 **Hyperlocal**: Diseñado específicamente para el Delta
- 🤖 **IA Contextual**: RAG con conocimiento local
- 🔄 **Multi-fuente**: Integración de múltiples APIs
- 📱 **Multi-plataforma**: Telegram, Web, WhatsApp

### Proyección Futura
- 🚤 **"Voy y Vuelvo"**: Sistema de ride-sharing fluvial
- 📡 **IoT Integration**: Sensores climáticos locales
- 🗺️ **Geolocalización**: Servicios basados en ubicación
- 🌐 **Replicabilidad**: Modelo exportable a otras zonas

---

## 📞 **CONTACTO Y CÓDIGO**

- 📧 **Email**: contacto@deltix.com.ar
- 💻 **GitHub**: github.com/marajadesantelmo/deltix
- 🤖 **Telegram**: @deltix_bot
- 🌐 **Web**: deltix.streamlit.app

### Tecnología Social + Open Source
*"Conectando comunidades rurales con innovación tecnológica accesible"*
