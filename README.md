<h1 align="center">
  <img src="bot_icon.png" alt="soy deltix" width="200"><br>
  Deltix... el bot del humedal<br>
  Delta inferior del Paraná - Buenos Aires
</h1>


Soy *Deltix, el bot del humedal!* Mi objetivo es ayudar a quienes habitan y visitan el delta inferior del Paraná. Fui diseñado para proporcionar información y servicios útiles a las personas que habitan o visitan la hermosa región del Delta del Tigre, en Buenos Aires. Por ahora mis principales funcionalidades son enviar pronósticos meteorológico y de maraes, horarios de lanchas colectivas y mandar los Memes Islenials más divertidos de la isla :P En el futuro te voy a poder ayudar también cuando estés buscando recomendaciones locales, información sobre actividades en el delta o simplemente quieras mantenerte al tanto de las novedades de la zona.

*Deltix es un proyecto abierto para colaborar. Contactanos si querés aportar con nuevas ideas y funcionalidades!*

<table>
  <tr>
    <td style="width: 70%;">
      <h2>Características Destacadas</h2>
      <ul>
        <li>🌊 Información de Mareas: Recibí el pronóstico de mareas en tiempo real para la región del Delta del Tigre.</li>
        <li>🌦️ Pronóstico Meteorológico: Consultá el pronóstico meteorológico de WindGurú para la zona.</li>
        <li>⛵ Colectivas: Tené siempre a mano los horarios de lanchas colectivas</li>
        <li>🤣 Memes Islenials: Descubrí los memes más divertidos de la isla.</li>
        <li>🤝 Colaborar y Sugerir: Compartí tus sugerencias y colaborá con el bot para mejorarlo.</li>
        <li>📤 Desuscribirte: Si deseas dejar de recibir actualizaciones, podés hacerlo en cualquier momento.</li>
        <li>✉️ Mensajear al Desarrollador: Mandale un mensajito al desarrollador del bot.</li>
      </ul>
    </td>
    <td style="width: 30%; vertical-align: top;">
      <img src="bot_qr.png" alt="Código QR del bot" width="150">
    </td>
  </tr>
</table>

### Podés interactuar con el bot en Telegram buscando a @deltix_del_humedal_bot o haciendo *[click acá](https://t.me/deltix_del_humedal_bot)*
<h1 align="center">
<img src="https://github.com/marajadesantelmo/deltix/assets/50368116/3a2ce1a0-0fc6-483d-a164-d2f89e92ba65" alt="Otra imagen" width="400">
</h1>

## Principales Scripts de la App

### `main.py`
Bot de telegram

### `app.py`
Aplicación Streamlit

### `scraping.py`
Este script se encarga de obtener los datos actualizados de mareas y pronósticos meteorológicos. Utiliza Selenium para tomar capturas de pantalla de Windguru y urllib para descargar la imagen de mareas del sitio del INA.

### `auto_push.py`
Este script verifica si hay cambios en el repositorio local y, de ser así, los sube automáticamente a GitHub. Es útil para mantener el repositorio actualizado con los últimos datos obtenidos por el script de scraping.

### `pull_data.yml`
Este archivo de configuración de GitHub Actions se encarga de actualizar los archivos `mareas.png` y `windguru.png` en el repositorio público. Se ejecuta cada vez que hay un push a la rama `main`.

## Desarrollo de la WebApp en Streamlit

Actualmente, se está desarrollando una versión del bot como una aplicación web utilizando Streamlit e integrando interacción conun  LLM. Esta versión permitirá a los usuarios interactuar con el bot directamente desde un navegador web, proporcionando una experiencia más accesible y amigable.


