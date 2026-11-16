# Cartelería digital CEP Lanzarote — Hisense VIDAA

Proyecto independiente del WordPress del CEP. Publica **solo los carteles originales** de noticias con una **fecha de cierre explícita que todavía no ha pasado**. No exige credenciales del blog.

## Qué incluye

- `site/index.html`: presentación a pantalla completa, sin títulos, con transición cada 10 segundos y sin recortar carteles.
- `scripts/update.py`: lee el RSS y las páginas públicas; extrae el plazo y la imagen.
- `.github/workflows/publicar.yml`: actualiza y publica automáticamente cada 4 horas (también al subir cambios y al ejecutarlo manualmente).
- `site/carteles.json`: datos generados automáticamente; no se edita a mano.
- `site/revision.json`: entradas que quedaron sin mostrar porque falta una fecha fiable, una imagen o ha habido algún error. Se puede abrir desde el navegador después de publicar.
- `config.json`: excepciones para noticias sin fecha o carteles incorrectos.

## PUBLICACIÓN EN GITHUB PAGES (sin usar WordPress)

1. Crear una cuenta en https://github.com si no tienes una.
2. Pulsar **New repository**, nombrarlo `cep-carteleria`, elegir **Public** y **Create repository**.
3. Subir **todos los archivos y carpetas de este ZIP**, conservando la estructura y, especialmente, la carpeta oculta `.github/workflows/`. Se puede hacer desde **Add file → Upload files**, o mediante Git. Si la interfaz no permite subir carpetas ocultas del ZIP extraído, crear manualmente `.github/workflows/publicar.yml` mediante **Add file → Create new file**.
4. En **Settings → Pages → Build and deployment → Source**, elegir **GitHub Actions**.
5. En la pestaña **Actions**, abrir **Actualizar cartelería y publicar web** y usar **Run workflow** si todavía no ha empezado. Verificar que acaba correctamente.
6. La web quedará en `https://TU_USUARIO.github.io/cep-carteleria/` (sustituir `TU_USUARIO` por el usuario real). Ese es el enlace para abrir en el navegador del Hisense VIDAA.
7. En el Hisense, abrir **Navegador** (puede llamarse Browser), introducir esa URL y activar pantalla completa si su versión lo admite. Desactivar salvapantallas/suspensión si las opciones del equipo lo permiten. Es posible que algunos modelos cierren el navegador al cabo de un tiempo: conviene hacer una prueba de varias horas.

### Qué significa «inscripción abierta»

El filtro usa únicamente la **fecha publicada** en el blog en un contexto de inscripción, solicitud o presentación. Si no hay fecha explícita, **no presupone que esté abierta**, aunque el cartel sea reciente. Si la fecha publicada es incorrecta, el programa no puede saberlo: revisa `revision.json` y `config.json`. Los enlaces de inscripción no se consultan ni se hace login para comprobar plazas disponibles.

**Importante:** no todas las noticias tienen un cartel válido; si falta la imagen, tampoco se muestran.

### Incluir manualmente una publicación

Si el blog no muestra el plazo o lo muestra incorrectamente, modifica `config.json` agregando la URL exacta de la noticia como clave, la fecha real comprobada (`AAAA-MM-DD`), y opcionalmente una URL directa de la imagen original:

```json
{
  "max_posts": 65,
  "feed_pages": 7,
  "exclude": [],
  "manual": {
    "https://www3.gobiernodecanarias.org/medusa/edublog/cprofeslanzarote/EJEMPLO/": {
      "close": "2026-12-15",
      "image": "https://www3.gobiernodecanarias.org/ruta-del-cartel.jpg"
    }
  }
}
```

Esto es **solo un ejemplo**, no una actividad real. No copiar la entrada de ejemplo literalmente. Al guardar los cambios en GitHub, la actualización se ejecuta automáticamente.

Para ocultar una entrada sin importar su fecha, añadir su URL a `exclude`.

### Cambiar intervalo de diapositivas

En `site/index.html`, editar `var DURATION = 10000;` (milisegundos). Por ejemplo, `15000` para 15 segundos.

### Cómo saber si está funcionando

- `https://TU_USUARIO.github.io/cep-carteleria/carteles.json` debe contener `entries` con las noticias filtradas.
- `https://TU_USUARIO.github.io/cep-carteleria/revision.json` contiene las que necesitan revisión.
- Si `entries` queda vacío, la página mostrará un mensaje en lugar de inventar actividades abiertas.
- En caso de problemas, mirar el registro de **Actions** en GitHub.

### Notas técnicas

- WordPress del Gobierno de Canarias es una fuente pública externa. Si modifica la estructura de sus imágenes o RSS, puede ser necesario adaptar el extractor.
- GitHub Actions permite programar ejecuciones, pero las tareas programadas pueden retrasarse. La TV también comprueba cada 15 minutos si se publicó una versión nueva y filtra localmente los plazos vencidos.
- Las imágenes se muestran desde el dominio original del blog, respetando el cartel sin alterar. El televisor necesita acceso de red a ese dominio.
- La página es estática y compatible con navegadores sencillos (sin frameworks). No podemos garantizar que **todos** los modelos Hisense/VIDAA mantengan el navegador abierto indefinidamente.
