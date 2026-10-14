import type { Metadata } from "next";
import { LegalShell, Site, H2, Identificativos } from "@/components/legal";

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
        Nuestro sitio web puede recopilar información personal como su nombre,
        información de contacto como su dirección de correo electrónico e
        información demográfica. También, cuando sea necesario, se puede requerir
        información específica para procesar un pedido o realizar una entrega o
        facturación.
      </p>

      <H2>Uso de la información recopilada</H2>
      <p>
        Nuestro sitio web utiliza la información con el fin de proporcionar el mejor
        servicio posible, en particular para realizar un seguimiento de los
        usuarios, para hacer un seguimiento de los pedidos en su caso, y para
        mejorar nuestros productos y servicios. Los correos electrónicos pueden ser
        enviados periódicamente a través de nuestro sitio con ofertas especiales,
        nuevos productos y otra información publicitaria que consideremos relevante
        para usted o que pueda proporcionarle un beneficio, estos correos
        electrónicos serán enviados a la dirección que usted proporcione y podrán
        ser cancelados en cualquier momento.
      </p>
      <p>
        <Site /> está altamente comprometido a mantener su información segura.
        Utilizamos los sistemas más avanzados y los actualizamos constantemente para
        asegurarnos de que no haya acceso no autorizado.
      </p>

      <H2>Cookies</H2>
      <p>
        Una cookie se refiere a un archivo que se envía con el fin de solicitar
        permiso para ser almacenado en su ordenador, mediante la aceptación de este
        archivo se crea y la cookie a continuación, sirve para tener información
        sobre el tráfico web, y también facilita futuras visitas a un sitio web
        recurrente. Otra función que tienen las cookies es que con ellas los sitios
        web pueden reconocerle individualmente y por lo tanto proporcionarle el
        mejor servicio personalizado en su sitio web.
      </p>
      <p>
        Nuestro sitio web utiliza cookies para identificar las páginas que son
        visitadas y su frecuencia. Esta información se utiliza únicamente para el
        análisis estadístico y, a continuación, se elimina de forma permanente.
        Usted puede eliminar las cookies de su ordenador en cualquier momento. Sin
        embargo, las cookies ayudan a proporcionar un mejor servicio de los sitios
        web, que no dan acceso a la información de su ordenador o de usted, a menos
        que desee y proporcionar directamente, las visitas a un sitio web. Usted
        puede aceptar o rechazar el uso de cookies, sin embargo, la mayoría de los
        navegadores aceptan cookies automáticamente ya que sirve para tener un mejor
        servicio web. También puede cambiar la configuración de su ordenador para
        rechazar las cookies. Si se rechazan, es posible que no pueda utilizar
        algunos de nuestros servicios.
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
        En cualquier momento usted puede restringir la recopilación o el uso de la
        información personal que se proporciona a nuestro sitio web. Cada vez que se
        le pida que rellene un formulario, como el formulario de registro de
        usuario, puede marcar o desmarcar la opción para recibir información por
        correo electrónico. Si ha marcado la casilla para recibir nuestro boletín o
        anuncio, puede cancelarlo en cualquier momento.
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
