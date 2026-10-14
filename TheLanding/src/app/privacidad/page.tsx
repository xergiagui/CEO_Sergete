import type { Metadata } from "next";
import { LegalShell, Site, A, H2, Identificativos } from "@/components/legal";

export const metadata: Metadata = {
  title: "Política de privacidad",
  description:
    "Política de privacidad: cómo recopilamos, usamos y protegemos la información obtenida a través de este sitio web.",
  alternates: { canonical: "/privacidad" },
  robots: { index: false, follow: true },
};

export default function Privacidad() {
  return (
    <LegalShell title="Política de privacidad">
      <p>
        La política de privacidad de <Site /> tiene por objeto informarle de la
        manera en que recopilamos y utilizamos la información obtenida a través de
        este sitio web.
      </p>
      <p>
        De ese modo la presente Política de Privacidad establece los términos en los
        que <Site /> utiliza y protege la información que sus usuarios proporcionan
        al utilizar su sitio web. Cuando le pedimos que rellene los campos de
        información personal con la que pueda ser identificado, lo hacemos
        asegurándonos de que sólo se utilizará de acuerdo con los términos de este
        documento. Sin embargo, esta Política de Privacidad puede cambiar de vez en
        cuando o ser actualizada y le recomendamos que revise esta página de vez en
        cuando para asegurarse de que está de acuerdo con dichos cambios.
      </p>

      <H2>DATOS IDENTIFICATIVOS</H2>
      <Identificativos />

      <H2>Información que se recopila</H2>
      <p>
        Este sitio web recopila los siguientes datos, según la acción que usted
        realice:
      </p>
      <ul className="list-disc space-y-2 pl-6">
        <li>
          Al solicitar un recurso, su dirección de correo electrónico, el recurso
          elegido y la página desde la que lo solicita.
        </li>
        <li>
          Al enviar el formulario de contacto, su nombre (opcional), su dirección de
          correo electrónico y el mensaje que escriba.
        </li>
        <li>
          De forma automática, datos de analítica propia: un identificador de sesión
          aleatorio, la página de procedencia y los parámetros de campaña de su
          primera visita, el tipo de dispositivo, el país (si lo facilita el
          servicio de alojamiento), el <em>user agent</em> del navegador y las
          acciones realizadas en el sitio (visitas, consulta de recursos y clics).
        </li>
      </ul>

      <H2>Uso de la información recopilada</H2>
      <p>
        Utilizamos su correo electrónico para llevarle al recurso que ha solicitado
        y, en el caso del formulario de contacto, para responder a su mensaje. Los
        datos de analítica se utilizan únicamente para conocer qué contenidos
        funcionan mejor y mejorar el sitio.
      </p>
      <p>
        Los datos se almacenan en Supabase, proveedor de almacenamiento. Los
        mensajes enviados desde el formulario de contacto también se reenvían por
        correo electrónico al titular del sitio mediante un servicio de envío de
        correo.
      </p>

      <H2>Cookies</H2>
      <p>
        Este sitio web no utiliza cookies propias ni de terceros. Únicamente guarda
        en su navegador, mediante almacenamiento local, un identificador de sesión y
        los datos de atribución de su primera visita, para la analítica propia
        descrita arriba. Puede eliminarlos en cualquier momento borrando los datos
        del sitio en la configuración de su navegador. Encontrará más información en
        nuestra <A href="/cookies">Política de cookies</A>.
      </p>

      <H2>Enlaces de terceros</H2>
      <p>
        Este sitio web puede contener enlaces a otros sitios que pueden ser de su
        interés. Una vez que haga clic en estos enlaces y abandone nuestro sitio,
        dejaremos de tener control sobre el sitio al que ha sido redirigido y, por
        lo tanto, no seremos responsables de los términos ni de la privacidad y
        protección de datos de esos otros sitios de terceros. Estos sitios están
        sujetos a sus propias políticas de privacidad, así que por favor revíselas
        para confirmar que está de acuerdo con ellas.
      </p>

      <H2>Control de su información personal</H2>
      <p>
        En cualquier momento puede solicitar el acceso, la rectificación o la
        supresión de los datos personales que nos ha facilitado, escribiendo a{" "}
        <A href="mailto:xergiagui.ventas@gmail.com">xergiagui.ventas@gmail.com</A>{" "}
        o a través de la página de <A href="/contacto">contacto</A>.
      </p>
      <p>
        Esta compañía no venderá, dará o distribuirá la información personal que se
        recoge sin su consentimiento, a menos que sea requerido por una orden
        judicial.
      </p>
      <p>
        <Site /> se reserva el derecho de cambiar los términos de esta Política de
        Privacidad en cualquier momento.
      </p>
    </LegalShell>
  );
}
