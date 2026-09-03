# Registro de Cambios - SafingData

Todos los cambios notables en este proyecto seran documentados en este archivo.

---

## [1.3.0] - 2026-09-03

### Nuevas caracteristicas

- **Soporte de Jump Host SSH (conexion a Tailscale sin cliente instalado)**:
  - Se agregaron los campos opcionales `jump_host` y `jump_user` a cada perfil
    de maquina SSH en `config.json`.
  - Cuando `jump_host` esta definido, la conexion se realiza en dos saltos:
    el cliente conecta primero al basti\u00f3n (que tiene Tailscale instalado) y
    a trav\u00e9s de el alcanza el nodo destino en la red privada (`100.x.x.x`).
    Esto permite hacer backups a servidores Tailscale sin necesidad de
    instalar ni configurar el cliente de Tailscale en la maquina de origen.
  - Implementado usando `paramiko.ProxyCommand` con la directiva nativa
    `ssh -W <host>:<port>`, lo que no requiere dependencias adicionales.
  - La ventana de configuracion muestra una nueva seccion "JUMP HOST" con
    los campos JUMP HOST y JUMP USER debajo de los datos del servidor.
  - La tarjeta de servidor en la pantalla principal muestra un badge
    "VIA JUMP HOST: ..." en amarillo cuando el salto esta configurado.
  - El boton "Probar conexion" tambien utiliza el Jump Host al verificar.
  - El log de conexion indica el Jump Host cuando esta activo.
  - Retrocompatible: los `config.json` existentes se migran automaticamente
    con `jump_host: ""` y `jump_user: ""` sin necesidad de intervencion.

---

## [1.2.0] - 2026-08-10

### Nuevas caracteristicas


- **Sincronizacion de backups entre maquinas (portabilidad)**:
  - Al conectarse al servidor SSH, el programa consulta automaticamente el
    directorio remoto y compara los backups existentes con el registro local.
  - Los backups encontrados en el servidor pero ausentes en el registro local
    son importados automaticamente, permitiendo verlos y descargarlos desde
    cualquier PC sin necesidad de copiar el archivo `data/session.json`.
  - Los backups importados se muestran en la lista con el estado "IMPORTADO"
    resaltado en amarillo para distinguirlos de los realizados desde esa maquina.
  - Los registros locales que ya no existen en el servidor se marcan como
    eliminados automaticamente al sincronizar.
- **Cancelacion de conexion SSH en progreso**:
  - Mientras el sistema se encuentra intentando conectar al servidor SSH, el boton de la cabecera cambia a "CANCELAR".
  - Presionar el boton durante el intento de conexion aborta el proceso de forma limpia y cierra los sockets asociados.

### Documentacion

- Se agrega el archivo `docs/portable-backups.md` con la descripcion completa
  del mecanismo de sincronizacion, los metadatos inferidos, las limitaciones
  conocidas y el flujo recomendado para usar el programa en un equipo nuevo.

---

## [1.1.0] - 2026-08-10

### Nuevas caracteristicas

- **Gestion de multiples maquinas SSH (nombres clave / aliases)**:
  - Se pueden agregar, editar y guardar multiples servidores SSH asignando a
    cada uno un nombre clave o alias distintivo (ej. "Servidor Casa",
    "VPS Produccion", "Trabajo").
  - Selector desplegable en el panel de configuracion para alternar la maquina
    activa rapidamente.
  - Opcion para agregar o eliminar perfiles de servidor SSH.
- **Privacidad y enmascaramiento de datos sensibles**:
  - En el panel "SERVIDOR SSH", el HOST y el USUARIO se ocultan por defecto
    con caracteres de proteccion.
  - Boton "mostrar / ocultar" en la tarjeta del servidor para revelar o esconder
    los datos sensibles.
- **Puerto SSH opcional**:
  - El puerto SSH pasa a ser opcional. Si se deja en blanco, el sistema usa
    el puerto predeterminado 22 con un placeholder descriptivo.
- **Prueba de conexion integrada**:
  - Boton "Probar conexion" en la ventana de configuracion para verificar
    credenciales sin iniciar una transferencia.
- **Migracion automatica de configuracion**:
  - Retrocompatibilidad asegurada: si se detecta un `config.json` con el formato
    anterior (servidor unico), se migra automaticamente a la estructura `machines`.

---

## [1.0.0] - Version inicial

- Lanzamiento inicial de SafingData SSH Backup Portable.
- Transferencias SSH/SFTP recursivas con paramiko.
- Seleccion de archivos y carpetas locales y monitoreo de espacio remoto.
- Interfaz grafica oscura con diseno tactico SpiderWeb en Tkinter.
