import type { Metadata } from "next";
import { LegalShell, A, H2, H3, UL, OL, Strong } from "@/components/legal";

export const metadata: Metadata = {
  title: "Política de cookies",
  description:
    "Política de cookies: qué cookies utiliza este sitio web, cómo desactivarlas o eliminarlas y guía para los navegadores más populares.",
  alternates: { canonical: "/cookies" },
  robots: { index: false, follow: true },
};

export default function Cookies() {
  return (
    <LegalShell title="Política de cookies">
      <p>
        Una <em>cookie</em> es un pequeño fichero de texto que se almacena en su
        navegador cuando visita casi cualquier página web. Su utilidad es que la web
        sea capaz de recordar su visita cuando vuelva a navegar por esa página. Las{" "}
        <em>cookies</em> suelen almacenar información de carácter técnico,
        preferencias personales, personalización de contenidos, estadísticas de uso,
        enlaces a redes sociales, acceso a cuentas de usuario, etc. El objetivo de
        la <em>cookie</em> es adaptar el contenido de la web a su perfil y
        necesidades, sin <em>cookies</em> los servicios ofrecidos por cualquier
        página se verían mermados notablemente. Si desea consultar más información
        sobre qué son las <em>cookies</em>, qué almacenan, cómo eliminarlas,
        desactivarlas, etc.,{" "}
        <A href="#mas-informacion">le rogamos se dirija a este enlace.</A>
      </p>

      <H2>Cookies utilizadas en este sitio web</H2>
      <p>
        Siguiendo las directrices de la Agencia Española de Protección de Datos
        procedemos a detallar el uso de <em>cookies</em> que hace esta web con el
        fin de informarle con la máxima exactitud posible.
      </p>
      <p>
        Este sitio web utiliza las siguientes <Strong>cookies propias</Strong>:
      </p>
      <UL>
        <li>
          Cookies de sesión, para garantizar que los usuarios que escriban
          comentarios en el blog sean humanos y no aplicaciones automatizadas. De
          esta forma se combate el <em>spam</em>.
        </li>
      </UL>
      <p>
        Este sitio web utiliza las siguientes <Strong>cookies de terceros</Strong>:
      </p>
      <UL>
        <li>
          Google Analytics: Almacena <em>cookies</em> para poder elaborar
          estadísticas sobre el tráfico y volumen de visitas de esta web. Al
          utilizar este sitio web está consintiendo el tratamiento de información
          acerca de usted por Google. Por tanto, el ejercicio de cualquier derecho
          en este sentido deberá hacerlo comunicando directamente con Google.
        </li>
        <li>
          Redes sociales: Cada red social utiliza sus propias <em>cookies</em> para
          que usted pueda pinchar en botones del tipo <em>Me gusta</em> o{" "}
          <em>Compartir</em>.
        </li>
      </UL>

      <H2>Desactivación o eliminación de cookies</H2>
      <p>
        En cualquier momento podrá ejercer su derecho de desactivación o eliminación
        de cookies de este sitio web. Estas acciones se realizan de forma diferente
        en función del navegador que esté usando.{" "}
        <A href="#navegadores">
          Aquí le dejamos una guía rápida para los navegadores más populares
        </A>
        .
      </p>

      <H2>Notas adicionales</H2>
      <UL>
        <li>
          Ni esta web ni sus representantes legales se hacen responsables ni del
          contenido ni de la veracidad de las políticas de privacidad que puedan
          tener los terceros mencionados en esta política de <em>cookies</em>.
        </li>
        <li>
          Los navegadores web son las herramientas encargadas de almacenar las{" "}
          <em>cookies</em> y desde este lugar debe efectuar su derecho a eliminación
          o desactivación de las mismas. Ni esta web ni sus representantes legales
          pueden garantizar la correcta o incorrecta manipulación de las{" "}
          <em>cookies</em> por parte de los mencionados navegadores.
        </li>
        <li>
          En algunos casos es necesario instalar <em>cookies</em> para que el
          navegador no olvide su decisión de no aceptación de las mismas.
        </li>
        <li>
          En el caso de las <em>cookies</em> de Google Analytics, esta empresa
          almacena las <em>cookies</em> en servidores ubicados en Estados Unidos y
          se compromete a no compartirla con terceros, excepto en los casos en los
          que sea necesario para el funcionamiento del sistema o cuando la ley
          obligue a tal efecto. Según Google no guarda su dirección IP. Google Inc.
          es una compañía adherida al Acuerdo de Puerto Seguro que garantiza que
          todos los datos transferidos serán tratados con un nivel de protección
          acorde a la normativa europea. Para cualquier duda o consulta acerca de
          esta política de <em>cookies</em> no dude en comunicarse con nosotros a
          través de la sección de contacto.
        </li>
      </UL>

      <H2 id="mas-informacion">Más información sobre las cookies</H2>

      <H3>¿Qué es una cookie?</H3>
      <p>
        Una <em>cookie</em> es un fichero de texto <Strong>inofensivo</Strong> que
        se almacena en su navegador cuando visita casi cualquier página web. La
        utilidad de la <em>cookie</em> es que la web sea capaz de recordar su visita
        cuando vuelva a navegar por esa página. Aunque mucha gente no lo sabe las{" "}
        <em>cookies</em> se llevan utilizando desde hace 20 años, cuando aparecieron
        los primeros navegadores para la World Wide Web.
      </p>

      <H3>¿Qué NO ES una cookie?</H3>
      <p>No es un virus, ni un troyano, ni un gusano, ni spam, ni spyware, ni abre ventanas pop-up.</p>

      <H3>
        ¿Qué información almacena una <em>cookie</em>?
      </H3>
      <p>
        Las <em>cookies</em> no suelen almacenar información sensible sobre usted,
        como tarjetas de crédito o datos bancarios, fotografías, su DNI o
        información personal, etc. Los datos que guardan son de carácter técnico,
        preferencias personales, personalización de contenidos, etc.
      </p>
      <p>
        El servidor web no le asocia a usted como persona si no a su navegador web.
        De hecho, si usted navega habitualmente con Internet Explorer y prueba a
        navegar por la misma web con Firefox o Chrome verá que la web no se da
        cuenta que es usted la misma persona porque en realidad está asociando al
        navegador, no a la persona.
      </p>

      <H3>
        ¿Qué tipo de <em>cookies</em> existen?
      </H3>
      <UL>
        <li>
          <em>Cookies</em> técnicas: Son las más elementales y permiten, entre otras
          cosas, saber cuándo está navegando un humano o una aplicación
          automatizada, cuándo navega un usuario anónimo y uno registrado, tareas
          básicas para el funcionamiento de cualquier web dinámica.
        </li>
        <li>
          <em>Cookies</em> de análisis: Recogen información sobre el tipo de
          navegación que está realizando, las secciones que más utiliza, productos
          consultados, franja horaria de uso, idioma, etc.
        </li>
        <li>
          <em>Cookies</em> publicitarias: Muestran publicidad en función de su
          navegación, su país de procedencia, idioma, etc.
        </li>
      </UL>

      <H3>
        ¿Qué son las <em>cookies</em> propias y las de terceros?
      </H3>
      <p>
        Las <em>cookies propias</em> son las generadas por la página que está
        visitando y las <em>de terceros</em> son las generadas por servicios o
        proveedores externos como Facebook, Twitter, Google, etc.
      </p>

      <H3>
        ¿Qué ocurre si desactivo las <em>cookies</em>?
      </H3>
      <p>
        Para que entienda el alcance que puede tener desactivar las{" "}
        <em>cookies</em> le mostramos unos ejemplos:
      </p>
      <UL>
        <li>
          No podrá compartir contenidos de esa web en Facebook, Twitter o cualquier
          otra red social.
        </li>
        <li>
          El sitio web no podrá adaptar los contenidos a sus preferencias
          personales, como suele ocurrir en las tiendas online.
        </li>
        <li>
          No podrá acceder al área personal de esa web, como por ejemplo{" "}
          <em>Mi cuenta</em>, o <em>Mi perfil</em> o <em>Mis pedidos</em>.
        </li>
        <li>
          Tiendas online: Le será imposible realizar compras online, tendrán que ser
          telefónicas o visitando la tienda física si es que dispone de ella.
        </li>
        <li>
          No será posible personalizar sus preferencias geográficas como franja
          horaria, divisa o idioma.
        </li>
        <li>
          El sitio web no podrá realizar analíticas web sobre visitantes y tráfico
          en la web, lo que dificultará que la web sea competitiva.
        </li>
        <li>
          No podrá escribir en el blog, no podrá subir fotos, publicar comentarios,
          valorar o puntuar contenidos. La web tampoco podrá saber si usted es un
          humano o una aplicación automatizada que publica <em>spam</em>.
        </li>
        <li>
          No se podrá mostrar publicidad sectorizada, lo que reducirá los ingresos
          publicitarios de la web.
        </li>
        <li>
          Todas las redes sociales usan <em>cookies</em>, si las desactiva no podrá
          utilizar ninguna red social.
        </li>
      </UL>

      <H3>
        ¿Se pueden eliminar las <em>cookies</em>?
      </H3>
      <p>
        Sí. No sólo eliminar, también bloquear, de forma general o particular para
        un dominio específico.
      </p>
      <p>
        Para eliminar las <em>cookies</em> de un sitio web debe ir a la
        configuración de su navegador y allí podrá buscar las asociadas al dominio
        en cuestión y proceder a su eliminación.
      </p>

      <H3 id="navegadores">
        Configuración de <em>cookies</em> para los navegadores más populares
      </H3>
      <p>
        A continuación, le indicamos cómo acceder a una <em>cookie</em> determinada
        del navegador <Strong>Chrome</Strong>. Nota: estos pasos pueden variar en
        función de la versión del navegador:
      </p>
      <OL>
        <li>
          Vaya a Configuración o Preferencias mediante el menú Archivo o bien
          pinchando el icono de personalización que aparece arriba a la derecha.
        </li>
        <li>
          Verá diferentes secciones, pinche la opción{" "}
          <em>Mostrar opciones avanzadas</em>.
        </li>
        <li>
          Vaya a <em>Privacidad</em>, <em>Configuración de contenido</em>.
        </li>
        <li>
          Seleccione <em>Todas las cookies y los datos de sitios</em>.
        </li>
        <li>
          Aparecerá un listado con todas las cookies ordenadas por dominio. Para que
          le sea más fácil encontrar las cookies de un determinado dominio
          introduzca parcial o totalmente la dirección en el campo{" "}
          <em>Buscar cookies</em>.
        </li>
        <li>
          Tras realizar este filtro aparecerán en pantalla una o varias líneas con
          las cookies de la web solicitada. Ahora sólo tiene que seleccionarla y
          pulsar la <em>X</em> para proceder a su eliminación.
        </li>
      </OL>

      <p>
        Para acceder a la configuración de cookies del navegador{" "}
        <Strong>Internet Explorer</Strong> siga estos pasos (pueden variar en
        función de la versión del navegador):
      </p>
      <OL>
        <li>
          Vaya a <em>Herramientas</em>, <em>Opciones de Internet</em>
        </li>
        <li>
          Haga click en <em>Privacidad</em>.
        </li>
        <li>Mueva el deslizador hasta ajustar el nivel de privacidad que desee.</li>
      </OL>

      <p>
        Para acceder a la configuración de cookies del navegador{" "}
        <Strong>Firefox</Strong> siga estos pasos (pueden variar en función de la
        versión del navegador):
      </p>
      <OL>
        <li>
          Vaya a <em>Opciones</em> o <em>Preferencias</em> según su sistema
          operativo.
        </li>
        <li>
          Haga click en <em>Privacidad</em>.
        </li>
        <li>
          En <em>Historial</em> elija{" "}
          <em>Usar una configuración personalizada para el historial</em>.
        </li>
        <li>
          Ahora verá la opción <em>Aceptar cookies</em>, puede activarla o
          desactivarla según sus preferencias.
        </li>
      </OL>

      <p>
        Para acceder a la configuración de cookies del navegador{" "}
        <Strong>Safari para OSX</Strong> siga estos pasos (pueden variar en función
        de la versión del navegador):
      </p>
      <OL>
        <li>
          Vaya a <em>Preferencias</em>, luego <em>Privacidad</em>.
        </li>
        <li>
          En este lugar verá la opción <em>Bloquear cookies</em> para que ajuste el
          tipo de bloqueo que desea realizar.
        </li>
      </OL>

      <p>
        Para acceder a la configuración de cookies del navegador{" "}
        <Strong>Safari para iOS</Strong> siga estos pasos (pueden variar en función
        de la versión del navegador):
      </p>
      <OL>
        <li>
          Vaya a <em>Ajustes</em>, luego <em>Safari</em>.
        </li>
        <li>
          Vaya a <em>Privacidad y Seguridad</em>, verá la opción{" "}
          <em>Bloquear cookies</em> para que ajuste el tipo de bloqueo que desea
          realizar.
        </li>
      </OL>

      <p>
        Para acceder a la configuración de cookies del navegador para dispositivos{" "}
        <Strong>Android</Strong> siga estos pasos (pueden variar en función de la
        versión del navegador):
      </p>
      <OL>
        <li>
          Ejecute el navegador y pulse la tecla <em>Menú</em>, luego <em>Ajustes</em>.
        </li>
        <li>
          Vaya a <em>Seguridad y Privacidad</em>, verá la opción{" "}
          <em>Aceptar cookies</em> para que active o desactive la casilla.
        </li>
      </OL>

      <p>
        Para acceder a la configuración de cookies del navegador para dispositivos{" "}
        <Strong>Windows Phone</Strong> siga estos pasos (pueden variar en función de
        la versión del navegador):
      </p>
      <OL>
        <li>
          Abra <em>Internet Explorer</em>, luego <em>Más</em>, luego{" "}
          <em>Configuración</em>
        </li>
        <li>
          Ahora puede activar o desactivar la casilla <em>Permitir cookies</em>.
        </li>
      </OL>
    </LegalShell>
  );
}
