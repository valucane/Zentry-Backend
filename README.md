# Zentry-Backend

Ecosistema digital integral para la gestión de ingresos y egresos en barrios cerrados mediante invitaciones, centralizando la gobernanza administrativa y operativa; además, garantizando el control de flujos de acceso mediante identidades digitales.

Este repositorio abarca el **Backend** de este sistema.

## Objetivos especificos

- Gestionar accesos de socios e invitados.
- Generar trazabilidad de ingresos y egresos de socios e invitados.
- Diseñar una interfaz comprensible para todo tipo de usuario.

## Cómo funciona

### Modulos existentes

- Barrios
- Administracion
- Invitaciones
- Reservas
- Eventos

### Barrios
 
Se encarga de centralizar los datos en un solo barrio. Solo consiste de un modelo: Barrio

**Modelos:**

- Barrio

### Administracion

Se encarga de la parte administrativa general del barrio, digamos las acciones que administracion tiene como responsabilidad. Se encarga de ABM de cuentas de socios, guardias, proveedores.

Tambien se encarga de los lotes y los puntos de acceso.

**Modelos:**

- Account
- Socio <--- Persona
- Proveedor <-- Persona
- Guardia <-- Persona
- Administrador <-- Persona
- Lote
- PuntoAcceso

Para habilitar el acceso de un residente, la administración debe crear el usuario
en Usuarios, asignarle una `Account` con rol `socio` y vincular esa cuenta al
registro del residente. El ingreso de residentes requiere el email y la contraseña
de ese usuario; no se crean cuentas de prueba durante el inicio de sesión.

Para configurar la cuenta administradora, definí `ZENTRY_ADMIN_EMAIL` y
`ZENTRY_ADMIN_PASSWORD` en el archivo `.env` local (no subas ese archivo al
repositorio) y ejecutá `python manage.py configurar_administrador`. El login de
administrador valida esas credenciales contra la cuenta real; no hay contraseñas
maestras guardadas en el código.

Una vez iniciada la sesión, un administrador puede crear otra cuenta
administradora con `POST /api/administradores/`. Enviá el token de sesión en
`Authorization: Token <token>` y un JSON con `nombre`, `dni`, `email` y
`password` (mínimo 8 caracteres). El endpoint devuelve `201 Created` con los
datos del perfil, nunca la contraseña. Residentes, guardias y usuarios sin
autenticación no pueden crear administradores.

Si un residente fue creado antes de habilitar la creación automática de cuentas,
definí `ZENTRY_RESIDENT_EMAIL` y `ZENTRY_RESIDENT_PASSWORD` en el `.env` local y
ejecutá `python manage.py configurar_acceso_residente`. El comando vincula el
residente existente sin duplicar su perfil.

La administración puede gestionar guardias en `/api/guardias/` o
`/api/guardia/` (GET, POST,
PATCH/PUT y DELETE). Para crear uno, enviá `nombre`, `email` y `password`;
la contraseña debe tener al menos 8 caracteres y nunca se devuelve en las
respuestas. Cada alta crea también una cuenta con rol `guardia`, que puede
iniciar sesión en `/api/auth/login/` indicando `rol: "guardia"`. La baja es
lógica y puede revertirse con `PUT /api/guardias/{id}/reactivate/`.
También se acepta `POST /api/guardia` sin barra final.

### Invitaciones

Se encarga de las invitaciones y accesos del barrio. Las diferentes formas de ingreso van a ser: Invitacion Unica (se vence una vez que se recepciona), Invitacion Recurrente (se vence al momento que se da de baja), Autorizacion de Proveedor (se autoriza a un proveedor a entrar a determinadas horas del dia). Ambas invitaciones van a estar constituidas en el modelo Invitación.

Van a existir invitaciones y luego un historico de invitaciones, donde se van a mostrar los accesos ya completados.

**Modelos:**

- Invitado <-- Persona
- Invitacion
- AutorizacionProveedor
- InvitacionHistorico
- RegistroAcceso

Para generar el QR, el frontend debe enviar la invitacion a `POST /api/invitaciones/`.
La respuesta incluye `qrToken`; el frontend codifica ese valor como QR (no los datos
personales del invitado). Al escanearlo, debe enviar `{"token": "<qrToken>"}` a
`POST /api/invitaciones/validar-qr/`. El backend verifica la vigencia antes de
registrar el ingreso: las invitaciones unicas se aceptan una vez y las recurrentes
se aceptan como maximo una vez por dia habilitado, dentro del rango de fechas elegido.

### Reservas

Se encarga de las reservas para los espacios comunes y la trazabilidad de los mismos, registrando el estado y problemas si existen

**Modelos:**

- LugarComun
- Reserva
- ReservaHistorico

### Eventos

Se encarga del boton de pánico. Esto significa la creacion de alertas, su recepcion y ademas llevar un registro de todas las veces que se uso.

**Modelos:**

- BotonPanico

## Documentación

Existen diagramas los cuales se utlizarán como documentación, ademas de un informe general. Aparte de esto vamos a tener dentro de este repositorio la documentación del sistema que va a cubrir cuestiones técnicas y de herramientas para tener en cuenta mientras se va desarrollando.

Toda esta documentación va a estar presentada en la entrega final.