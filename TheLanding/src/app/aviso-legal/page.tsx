import type { Metadata } from "next";
import { LegalShell, Site, H2, Identificativos } from "@/components/legal";

export const metadata: Metadata = {
  title: "Aviso legal",
  description:
    "Aviso legal: datos identificativos del titular, condiciones de uso, propiedad intelectual y legislación aplicable.",
  alternates: { canonical: "/aviso-legal" },
  robots: { index: false, follow: true },
};

export default function AvisoLegal() {
  return (
    <LegalShell title="Aviso legal">
      <p>
        <Site /> se reserva expresamente el derecho a modificar el presente Aviso
        Legal. El usuario reconoce y acepta que es su responsabilidad revisar el
        Sitio Web y este Aviso Legal.
      </p>

      <H2>Aceptación del usuario</H2>
      <p>
        El presente Aviso Legal regula el acceso y uso de la página web <Site /> a
        disposición de los usuarios de Internet. Se entenderá por Usuario la
        persona que acceda, navegue, utilice o participe en los servicios y
        actividades del sitio web. El acceso y navegación de un usuario implica la
        aceptación sin reservas de este Aviso Legal.
      </p>

      <H2>DATOS IDENTIFICATIVOS</H2>
      <Identificativos />

      <H2>Uso de la página web</H2>
      <p>
        El usuario se compromete a utilizar <Site />, los contenidos y servicios de
        conformidad con la Ley, el presente Aviso Legal, las buenas costumbres y el
        orden público. Asimismo, el Usuario se compromete a no utilizarlo con fines
        o efectos ilícitos o contrarios al contenido del presente Aviso Legal,
        lesivos de los intereses o derechos de terceros, o que de cualquier forma
        puedan dañar, inutilizar o deteriorar el sitio web o sus servicios o impedir
        el normal disfrute del sitio web por otros Usuarios.
      </p>
      <p>
        El usuario se compromete a no obstaculizar el acceso de otros usuarios al
        servicio de acceso mediante el consumo masivo de los recursos informáticos a
        través de los cuales se presta el servicio, así como a realizar acciones que
        dañen, interrumpan o generen errores en dichos sistemas o servicios. El
        usuario se compromete a hacer un uso adecuado de los contenidos y servicios
        y a no emplearlos para incurrir en actividades ilícitas o contrarias a la
        buena fe.
      </p>

      <H2>Limitación de garantías y responsabilidad</H2>
      <p>
        <Site /> se compromete a realizar los máximos esfuerzos para evitar
        cualquier error en los contenidos que pudieran aparecer en la Web. En
        cualquier caso, <Site /> quedará exenta de cualquier responsabilidad
        derivada de los errores en los contenidos que pudieran aparecer en la Web,
        siempre que no sean imputables a la misma.
      </p>

      <H2>Propiedad intelectual e industrial. Todos los derechos reservados.</H2>
      <p>
        Todos los derechos de propiedad intelectual e industrial del sitio web así
        como de sus contenidos (textos, imágenes, sonidos, audio, vídeo, diseños,
        creatividades, software) pertenecen a <Site />
      </p>
      <p>
        Queda expresamente prohibida la reproducción, distribución y comunicación
        pública, incluida la forma en que se pone a disposición, de todo o parte de
        los contenidos de este sitio web con fines comerciales, en cualquier soporte
        y por cualquier medio técnico, sin autorización. El usuario se compromete a
        respetar los derechos de Propiedad Industrial e Intelectual titularidad de{" "}
        <Site /> y de terceros.
      </p>
      <p>
        El usuario podrá visualizar todos los elementos, imprimirlos, copiarlos y
        almacenarlos en el disco duro de su ordenador o en cualquier otro soporte
        físico siempre que sea, única y exclusivamente, para su uso personal y
        privado, quedando, por tanto, terminantemente prohibida su utilización con
        fines comerciales, su distribución, modificación, alteración o
        descompilación.
      </p>

      <H2>Responsabilidad por los contenidos y enlaces de terceros</H2>
      <p>
        <Site /> no se responsabiliza de la legalidad de las páginas web de terceros
        desde las que se pueda acceder al portal. <Site /> tampoco se responsabiliza
        de la legalidad de las páginas web de terceros a las que se pueda enlazar
        desde este portal.
      </p>
      <p>
        <Site /> no será responsable del uso que terceros hagan de la información
        publicada en el portal, ni de los daños o perjuicios económicos que, directa
        o indirectamente, produzcan o puedan producir daños económicos, materiales o
        de datos causados por el uso de dicha información.
      </p>

      <H2>Derecho aplicable</H2>
      <p>
        La legislación aplicable en caso de litigio o conflicto de interpretación de
        los términos que integran el presente aviso legal, así como cualquier
        cuestión relacionada con los servicios de este portal, será la legislación
        española.
      </p>
    </LegalShell>
  );
}
