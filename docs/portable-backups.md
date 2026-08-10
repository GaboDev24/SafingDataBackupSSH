# Portabilidad de backups entre maquinas

## El problema

SafingData guarda un registro local de todos los backups realizados en el archivo
`data/session.json`. Este archivo actua como indice: contiene el ID de cada backup,
la fecha en que se realizo, los paths locales que se subieron y el tamano en bytes.

Cuando el programa se transfiere a otra PC (por ejemplo, copiando la carpeta del
ejecutable a una memoria USB y ejecutandolo en un segundo equipo), el archivo
`data/session.json` puede estar vacio o contener registros de otra maquina. En ese
caso, la lista "Backups activos" del panel derecho aparece vacia aunque los backups
existan fisicamente en el servidor SSH.

## Sincronizacion automatica al conectarse

A partir de esta version, cada vez que se establece una conexion SSH el programa
ejecuta una sincronizacion automatica de la lista de backups:

1. Se consulta el directorio remoto base (el configurado en "DIR. REMOTO") mediante
   SFTP y se obtiene la lista de subdirectorios existentes. Cada subdirectorio
   representa un backup.

2. Los IDs encontrados en el servidor que no existan en el session.json local
   se importan automaticamente como nuevas entradas.

3. Los registros locales cuyo ID ya no exista en el servidor se marcan como
   eliminados en el indice local. Esto ocurre solo si no habian sido borrados
   previamente de forma explicita mediante el boton Eliminar.

4. Los backups importados aparecen en la tabla con el estado IMPORTADO resaltado
   en amarillo, a diferencia del estado GUARDADO en verde de los backups realizados
   desde esa PC.

5. Al finalizar la sincronizacion, el log de la aplicacion indica cuantos backups
   nuevos fueron importados desde el servidor.

## Metadatos inferidos

Cuando se importa un backup desde el servidor, no toda la informacion original esta
disponible en el registro local. El sistema infiere los datos de la siguiente manera:

| Campo       | Valor inferido                                                 |
|-------------|----------------------------------------------------------------|
| Fecha       | Extraida del nombre si sigue el patron backup_YYYYMMDD_HHMMSS |
| Tamano      | 0 (se muestra como un guion en la tabla)                       |
| Paths       | Lista vacia (no se conocen las rutas originales)               |
| Importado   | true (marca la entrada como importada desde el servidor)       |

El nombre de backup generado automaticamente por la aplicacion sigue el patron
backup_YYYYMMDD_HHMMSS, por lo que la inferencia de fecha funcionara en la
mayoria de los casos. Si el usuario asigno un nombre personalizado al backup, se
usara la fecha y hora del momento de la sincronizacion como valor de referencia.

## Limitaciones

- El tamano mostrado para los backups importados es 0 porque calcularlo
  requeriria recorrer el arbol de directorios remoto de forma recursiva, lo que
  en backups grandes podria tardar varios minutos. Esta informacion no es
  necesaria para descargar o eliminar el backup.

- Los paths originales no se pueden recuperar. Esto no afecta la descarga
  del backup, pero si impide reutilizar esa seleccion en un nuevo backup.

- Si el directorio remoto base no existe aun en el servidor (primera conexion
  antes de cualquier backup), la sincronizacion devolvera 0 resultados y no
  reportara error.

## Flujo recomendado en un equipo nuevo

1. Abrir el programa en el equipo nuevo.
2. Verificar que la configuracion de la maquina SSH sea correcta (host, puerto,
   usuario, directorio remoto).
3. Hacer clic en CONECTAR e ingresar la contrasena SSH.
4. La sincronizacion se ejecuta automaticamente. Si habia backups en el servidor,
   apareceran en la lista con el estado IMPORTADO.
5. Seleccionar el backup deseado y hacer clic en Descargar.

No es necesario copiar el archivo data/session.json entre PCs. El servidor
SSH es la fuente de verdad para la lista de backups disponibles.

## Archivo de registro local

El archivo data/session.json tiene la siguiente estructura para cada entrada:

```json
{
  "backup_20260810_102134": {
    "created_at": "2026-08-10T10:21:34.505877",
    "paths": ["C:\\Users\\Usuario\\Documentos\\Proyecto"],
    "size_bytes": 70185353,
    "deleted": false,
    "imported": false
  },
  "backup_20260810_150022": {
    "created_at": "2026-08-10T15:00:22",
    "paths": [],
    "size_bytes": 0,
    "deleted": false,
    "imported": true
  }
}
```

El campo imported distingue los backups realizados localmente de los importados
del servidor. Los campos paths y size_bytes estaran vacios o en cero para las
entradas importadas.
