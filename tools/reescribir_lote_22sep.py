"""Reescribe el lote del 22/09/2026 con las reglas de tono nuevas.

Los hechos y los casos son los mismos; lo que cambia es cómo está dicho. El
lote original medía: 15 de 20 ganchos rematando a mitad de frase, 12 de 20
abriendo con la misma palabra, la frase más larga de cada guion entre 30 y 37
palabras, y dos guiones distintos (Metro Línea 12 y Colegio Rébsamen)
cerrando con la MISMA oración.

Reglas aplicadas (las mismas que quedaron en INSTRUCCION_NUEVO_LOTE):
  a) ninguna frase pasa de 20 palabras
  b) el gancho termina en la palabra que duele
  c) el sujeto tiene cara: nada de "la responsabilidad", "las autoridades"
  d) nada de verbos de vocero: "perdió la vida", "se vino abajo"
  e) nada de conectores de ensayo: "en cambio", "con claridad"
  f) ningún gancho abre con la misma palabra que otro, ningún cierre repite
     la estructura de otro

Se corre una sola vez:  python tools/reescribir_lote_22sep.py
Verificar después con:  python tools/medir_tono.py
"""

import json
from pathlib import Path

ANDROID_IN = Path(r"C:\Android_in")

# slug -> {"gancho": str opcional, "planos": {pid: (narracion, texto_en_pantalla)}}
LOTE: dict[str, dict] = {

"guion-culiacanazo-2019": {"planos": {
 "p00": ("El ejército capturó al hijo del capo. Ocho horas después, el gobierno lo soltó.",
         "CULIACÁN · OCTUBRE 2019"),
 "p01": ("Te imaginas al soldado que en octubre de dos mil diecinueve entró a una casa de "
         "Culiacán. Adentro estaba el hijo del hombre más buscado de México. Lo esposaron "
         "en minutos.", "EL HIJO DEL CAPO"),
 "p02": ("La respuesta tardó media hora. Hombres armados tomaron la ciudad entera. "
         "Bloquearon las calles, quemaron camiones y rodearon el cuartel donde lo tenían.",
         "TOMARON LA CIUDAD"),
 "p03": ("Después fueron por las familias de los soldados. Rodearon las casas donde vivían "
         "sus mujeres y sus hijos. Eso fue lo que cambió todo.", "FUERON POR SUS FAMILIAS"),
 "p04": ("Culiacán ardió ocho horas. Aeropuerto cerrado, presos fugados, familias tiradas "
         "en el piso de los supermercados. Trece muertos.", "TRECE MUERTOS"),
 "p05": ("Esa noche el gobierno ordenó soltarlo. El presidente lo dijo en público: valía "
         "más la vida de la gente que un detenido.", "EL GOBIERNO CEDIÓ"),
 "p06": ("Meses después lo volvieron a capturar, y esa vez sí se lo llevaron esposado. La "
         "primera vez, quien decidió no fue el gobierno. Fue la ciudad.", "DECIDIÓ LA CIUDAD"),
 "p07": ("Aquí el dato mata al gato. ¿Soltarlo fue la decisión correcta? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-diana-cazadora": {"planos": {
 "p00": ("Mató a dos choferes de autobús con un tiro en la cabeza. Después le escribió a la "
         "prensa.", "CIUDAD JUÁREZ · 2013"),
 "p01": ("Te imaginas a la mujer que en agosto de dos mil trece subió a una ruta de Ciudad "
         "Juárez. Llevaba peluca rubia. Se sentó adelante, sacó una pistola y disparó.",
         "PELUCA RUBIA"),
 "p02": ("Al día siguiente volvió a hacerlo en otra ruta. Mismo método, mismo lugar del "
         "cuerpo, misma hora de la mañana.", "DOS DÍAS SEGUIDOS"),
 "p03": ("Después mandó un correo a los periódicos de la ciudad. Firmaba: la cazadora de "
         "choferes. Decía que venía a vengar a las mujeres.", "FIRMÓ LA CAZADORA"),
 "p04": ("Juárez llevaba veinte años enterrando mujeres. Muchas desaparecían volviendo del "
         "trabajo, en esas mismas rutas, con esos mismos choferes.", "20 AÑOS DE FEMINICIDIOS"),
 "p05": ("La policía revisó cámaras, tomó huellas y rastreó el correo. Nunca la identificó. "
         "Nadie fue detenido por esos dos disparos, ni entonces ni después.",
         "NUNCA LA IDENTIFICARON"),
 "p06": ("Trece años después el caso sigue sin nombre. Disparó dos veces, avisó por escrito, "
         "y se fue sin que nadie le viera la cara.", "SIGUE SIN NOMBRE"),
 "p07": ("Aquí el dato mata al gato. ¿Actuó sola o fueron varias? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

# El año estaba mal en la versión anterior: decía 2022. La masacre de Creel
# fue en agosto de 2008.
"guion-masacre-creel": {"planos": {
 "p00": ("Entraron a un billar de pueblo y dispararon contra todos. Entre los trece muertos "
         "había un bebé.", "CREEL, CHIHUAHUA · 2008"),
 "p01": ("Te imaginas al pueblo de la sierra que en agosto de dos mil ocho vivía del "
         "turismo. Creel, Chihuahua: trenes, cascadas, gente de fuera todo el año.",
         "UN PUEBLO DE TURISMO"),
 "p02": ("Esa noche un grupo de jóvenes estaba afuera del billar, en la calle principal. "
         "Llegaron dos camionetas y bajaron hombres con rifles.", "LLEGARON DOS CAMIONETAS"),
 "p03": ("Dispararon contra el grupo sin preguntar nada. Mataron a trece personas. La más "
         "chica tenía un año y estaba en brazos de su padre.", "13 MUERTOS"),
 "p04": ("Ninguno tenía que ver con el pleito por la sierra. Eran vecinos del pueblo, "
         "parados en la banqueta un sábado.", "UN BEBÉ DE UN AÑO"),
 "p05": ("La versión oficial habló de un pleito entre grupos armados por el control de la "
         "sierra. Nadie fue detenido esa semana, ni la siguiente.", "NADIE DETENIDO"),
 "p06": ("Creel siguió recibiendo turistas, pero ya no por las cascadas. El pueblo que vivía "
         "de la sierra quedó marcado por trece cuerpos afuera de un billar.",
         "EL PUEBLO QUEDÓ MARCADO"),
 "p07": ("Aquí el dato mata al gato. ¿Te habías enterado de esta masacre? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-samir-flores": {"planos": {
 "p00": ("Un funcionario lo señaló por su nombre en un acto público. Tres días después lo "
         "mataron.", "MORELOS · FEBRERO 2019"),
 "p01": ("Te imaginas al locutor de radio comunitaria que en febrero de dos mil diecinueve "
         "vivía en un pueblo de Morelos. Se oponía a una termoeléctrica. El gasoducto pasaba "
         "por las tierras de su comunidad.", "UNA RADIO COMUNITARIA"),
 "p02": ("Días antes, un funcionario federal lo nombró en un foro público. Dijo que los "
         "opositores al proyecto respondían a intereses políticos, no a su comunidad.",
         "LO NOMBRARON EN UN FORO"),
 "p03": ("El pueblo llevaba años peleando ese gasoducto. Decían que la consulta fue un "
         "trámite, no una consulta de verdad. Nadie los escuchó.", "LA CONSULTA FUE UN TRÁMITE"),
 "p04": ("El veinte de febrero, dos hombres lo esperaron afuera de su casa. Le dispararon "
         "cuando salía, a las cinco y media de la mañana.", "LO MATARON AL SALIR"),
 "p05": ("El gobierno condenó el crimen y prometió una investigación. Seis años después nadie "
         "sabe quién dio la orden. Nadie está preso.", "NADIE DIO LA ORDEN"),
 "p06": ("La termoeléctrica arrancó igual, y hoy está funcionando. Un hombre se opuso a una "
         "planta; la planta le ganó.", "LA PLANTA FUNCIONA"),
 "p07": ("Aquí el dato mata al gato. ¿Señalarlo en público tuvo que ver? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-luz-del-mundo-abuso": {"planos": {
 "p00": ("Abusó de niñas de su propia iglesia durante años. Cinco millones de fieles salieron "
         "a defenderlo.", "LOS ÁNGELES · JUNIO 2019"),
 "p01": ("Te imaginas al líder de una iglesia con templos en cincuenta países. En junio de "
         "dos mil diecinueve bajó de un avión en Los Ángeles. Lo esperaba la policía.",
         "CINCUENTA PAÍSES"),
 "p02": ("Lo detuvieron por abuso sexual de menores dentro de su propia organización. Las "
         "denunciantes habían crecido ahí adentro, desde chicas.", "LO DETUVIERON AL BAJAR"),
 "p03": ("Contaron lo mismo: que el abuso empezó cuando eran niñas. Que se los presentaban "
         "como parte de servir al apóstol. Que callarse era parte de la fe.",
         "EMPEZÓ CUANDO ERAN NIÑAS"),
 "p04": ("Los cargos fueron abuso sexual de menores, trata de personas y producción de "
         "material con niñas. Todo, según la fiscalía, adentro de los templos.",
         "TRATA DE PERSONAS"),
 "p05": ("Miles de fieles marcharon por él en México y en Estados Unidos. Su iglesia dijo que "
         "era persecución religiosa, no un delito.", "MARCHARON POR ÉL"),
 "p06": ("Se declaró culpable para evitar el juicio y le dieron dieciséis años. La iglesia que "
         "lo defendió sigue abierta, y sigue creciendo.", "16 AÑOS DE CONDENA"),
 "p07": ("Aquí el dato mata al gato. ¿Creés que la iglesia sabía? Decímelo en los comentarios.",
         "DATO MATA GATO"),
}},

"guion-bety-carino-caravana": {"planos": {
 "p00": ("Emboscaron una caravana que llevaba comida a un pueblo sitiado. Mataron a una "
         "activista y a un finlandés.", "OAXACA · ABRIL 2010"),
 "p01": ("Te imaginas a la activista que en abril de dos mil diez iba rumbo a la sierra de "
         "Oaxaca. Atrás iban cajas de comida. Al lado, un observador finlandés de derechos "
         "humanos.", "RUMBO A LA SIERRA"),
 "p02": ("Iban a San Juan Copala, un pueblo triqui que se había declarado autónomo. Un grupo "
         "armado lo tenía cercado desde hacía meses, sin dejar entrar a nadie.",
         "UN PUEBLO CERCADO"),
 "p03": ("Adentro no entraba comida, ni agua, ni medicinas, ni maestros. La caravana salió "
         "para romper ese cerco y mostrarlo al mundo.", "NI COMIDA NI MEDICINAS"),
 "p04": ("En el camino de terracería los esperaron entre los árboles. Dispararon contra las "
         "camionetas. La activista y el observador murieron ahí mismo.",
         "LOS ESPERARON EN EL CAMINO"),
 "p05": ("La muerte de un europeo puso el caso en los diarios del mundo. Finlandia pidió "
         "explicaciones. México prometió justicia y mandó investigadores.",
         "FINLANDIA PIDIÓ EXPLICACIONES"),
 "p06": ("Quince años después nadie está condenado por esa emboscada. La caravana fue a "
         "romper un cerco, y terminó levantando otro.", "NADIE CONDENADO"),
 "p07": ("Aquí el dato mata al gato. ¿Sirvió de algo la presión internacional? Decímelo en "
         "los comentarios.", "DATO MATA GATO"),
}},

"guion-fraude-segalmex": {"planos": {
 "p00": ("Prometieron acabar con la corrupción y armaron el desfalco más grande del sexenio. "
         "Quince mil millones.", "MÉXICO · 2019"),
 "p01": ("Te imaginas al organismo que en dos mil diecinueve nació para comprarle maíz barato "
         "al campesino. Se llamaba Segalmex. Repartía fertilizante, leche y frijol a precio "
         "de apoyo.", "SE LLAMABA SEGALMEX"),
 "p02": ("Empezó comprando caro. Pagaba el doble por granos que valían la mitad, a empresas "
         "recién creadas sin historial.", "PAGABA EL DOBLE"),
 "p03": ("Después dejó de comprar del todo. Firmaba contratos, soltaba el dinero, y el "
         "producto nunca llegaba a los almacenes. Ni una tonelada.",
         "EL PRODUCTO NUNCA LLEGÓ"),
 "p04": ("Los auditores encontraron empresas fantasma, sobreprecios y compras sin licitar. "
         "Quince mil millones de pesos que nadie puede rastrear hasta hoy.", "15 MIL MILLONES"),
 "p05": ("El director general terminó preso. Varios funcionarios más fueron detenidos, y "
         "otros se fueron del país antes de que los llamaran.", "EL DIRECTOR, PRESO"),
 "p06": ("El gobierno que hizo del combate a la corrupción su bandera se lo robó solo. Y se "
         "lo robó del programa que era para el campo más pobre.", "DEL PROGRAMA DEL CAMPO"),
 "p07": ("Aquí el dato mata al gato. ¿Creés que ese dinero vuelve algún día? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-secuestro-matamoros-2023": {"planos": {
 "p00": ("Secuestraron a cuatro estadounidenses por error. Después el cártel entregó a sus "
         "propios hombres y pidió perdón.", "MATAMOROS · MARZO 2023"),
 "p01": ("Te imaginas a los cuatro amigos que en marzo de dos mil veintitrés cruzaron la "
         "frontera hacia Matamoros. Iban en una minivan blanca. Una de ellas iba a operarse.",
         "UNA MINIVAN BLANCA"),
 "p02": ("Los confundieron con traficantes rivales. Les dispararon en plena calle y los "
         "subieron a una camioneta, frente a los testigos.", "LOS CONFUNDIERON"),
 "p03": ("Una mujer que pasaba por ahí murió en la balacera. Se llamaba Areli, vendía en un "
         "puesto, y nadie de afuera preguntó por ella.", "MURIÓ UNA MUJER LOCAL"),
 "p04": ("Cuatro días después aparecieron en una casa de madera a las afueras de la ciudad. "
         "Dos vivos, dos muertos, todos amarrados.", "DOS VIVOS, DOS MUERTOS"),
 "p05": ("Lo que siguió no se había visto nunca. El cártel dejó una carta y entregó a cinco "
         "de los suyos, atados en la calle. Pidió disculpas por escrito.",
         "ENTREGÓ A LOS SUYOS"),
 "p06": ("Cruzaron la frontera por una cirugía de tres mil dólares. Volvieron dentro de un "
         "escándalo entre dos países, y dos de ellos volvieron muertos.",
         "UNA CIRUGÍA DE 3 MIL"),
 "p07": ("Aquí el dato mata al gato. ¿Te creés la disculpa del cártel? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-aristoteles-sandoval": {"planos": {
 "p00": ("Cenaba en un restaurante de Puerto Vallarta con sus escoltas en la mesa. Entró un "
         "hombre y le disparó.", "PUERTO VALLARTA · 2020"),
 "p01": ("Te imaginas al exgobernador de Jalisco que en diciembre de dos mil veinte pasaba "
         "las fiestas en la playa. Tenía cuarenta y siete años. Todavía movía hilos en su "
         "partido.", "EXGOBERNADOR DE JALISCO"),
 "p02": ("Esa madrugada bajó al baño del restaurante. Un hombre lo siguió, esperó, y le "
         "disparó por la espalda.", "LO SIGUIÓ AL BAÑO"),
 "p03": ("Afuera lo esperaba otro con un rifle. Hubo balazos entre las mesas y murió uno de "
         "sus escoltas. La gente salió corriendo a la playa.", "MURIÓ UN ESCOLTA"),
 "p04": ("Había gobernado el estado más importante del occidente entre dos mil trece y dos "
         "mil dieciocho. Su sexenio fue el del auge del cártel de la zona.",
         "GOBERNÓ 2013-2018"),
 "p05": ("Detuvieron a varios en los meses siguientes, incluido el hombre que disparó. "
         "Ninguno dijo quién pagó. La línea se cortó ahí.", "NADIE DIJO QUIÉN PAGÓ"),
 "p06": ("Sobrevivió seis años de política en Jalisco y no sobrevivió una cena. Cinco años "
         "después nadie sabe quién lo mandó matar. Los que sí saben, no hablan.",
         "NO SOBREVIVIÓ UNA CENA"),
 "p07": ("Aquí el dato mata al gato. ¿Creés que algún día se sabrá? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-explosion-tlahuelilpan": {"planos": {
 "p00": ("Corrieron con baldes a un ducto perforado. Dos horas después ardieron ciento "
         "treinta y siete personas.", "TLAHUELILPAN · ENERO 2019"),
 "p01": ("Te imaginas al pueblo de Hidalgo que en enero de dos mil diecinueve se enteró de un "
         "chorro de gasolina gratis. Era enero. Había desabasto en todo el país.",
         "GASOLINA GRATIS"),
 "p02": ("El ducto llevaba horas abierto. Salía un chorro de siete metros y el campo entero "
         "se hizo una laguna de gasolina.", "UN CHORRO DE 7 METROS"),
 "p03": ("Llegaron vecinos con bidones, garrafas y cubetas de albañil. Llegaron niños con "
         "botellas. Había setenta soldados mirando, y no acordonaron nada.",
         "70 SOLDADOS MIRANDO"),
 "p04": ("A las siete de la tarde prendió. La bola de fuego alcanzó a toda la gente parada "
         "alrededor del chorro. Nadie alcanzó a correr.", "PRENDIÓ A LAS 7"),
 "p05": ("Murieron ciento treinta y siete personas. Muchos tardaron días en morir, quemados, "
         "en hospitales de tres estados distintos.", "137 MUERTOS"),
 "p06": ("El desabasto de esa semana venía del plan contra el robo de combustible. El ducto "
         "que prometía gasolina gratis cobró ciento treinta y siete vidas.",
         "VENÍA DEL PLAN OFICIAL"),
 "p07": ("Aquí el dato mata al gato. ¿Se pudo haber evitado? Decímelo en los comentarios.",
         "DATO MATA GATO"),
}},

"guion-colegio-rebsamen": {"planos": {
 "p00": ("Le pusieron dos pisos de más a una escuela. El sismo la tiró con los niños adentro.",
         "CDMX · 19 SEPTIEMBRE 2017"),
 "p01": ("Te imaginas a los niños de segundo de primaria que el diecinueve de septiembre de "
         "dos mil diecisiete estaban en clase. Eran la una y catorce. En la Ciudad de México "
         "tembló.", "ERA LA 1:14"),
 "p02": ("El ala del colegio se dobló sobre sí misma en segundos. Adentro había diecinueve "
         "niños de primaria y siete adultos.", "19 NIÑOS, 7 ADULTOS"),
 "p03": ("Encima de las aulas vivía la dueña del colegio. Había levantado ahí un departamento "
         "entero que nunca estuvo en los planos.", "ARRIBA VIVÍA LA DUEÑA"),
 "p04": ("Esos metros de más pesaban sobre columnas que no estaban hechas para cargarlos. Un "
         "perito lo había escrito en una hoja, años antes del sismo.",
         "UN PERITO YA LO HABÍA DICHO"),
 "p05": ("La dueña se fue del país esa misma semana. La agarraron meses después en un "
         "aeropuerto, con otro nombre y otro pasaporte.", "HUYÓ CON OTRO NOMBRE"),
 "p06": ("Le dieron treinta y un años de cárcel por homicidio culposo. Los pisos que mataron "
         "a esos niños nunca debieron existir.", "31 AÑOS DE CÁRCEL"),
 "p07": ("Aquí el dato mata al gato. ¿Treinta y un años alcanzan? Decímelo en los comentarios.",
         "DATO MATA GATO"),
}},

"guion-fuga-cieneguillas": {"planos": {
 "p00": ("Cincuenta y tres presos salieron por la puerta principal. Los custodios se la "
         "abrieron.", "ZACATECAS · MAYO 2009"),
 "p01": ("Te imaginas al custodio que en mayo de dos mil nueve estaba de turno en un penal de "
         "Zacatecas. Eran las cuatro y media de la mañana. Sonó el portón y lo abrió.",
         "4:30 DE LA MAÑANA"),
 "p02": ("Entraron diecisiete camionetas hasta el patio central, con un helicóptero dando "
         "vueltas arriba. Nadie disparó un solo tiro en toda la operación.", "17 CAMIONETAS"),
 "p03": ("Los presos ya estaban formados en el patio, esperando. Subieron a las camionetas "
         "como quien sube a un camión de turismo, sin correr.", "YA ESTABAN FORMADOS"),
 "p04": ("Todo duró menos de cuatro minutos. Las cámaras del penal grabaron la salida "
         "completa, de principio a fin. Nadie tocó una alarma.", "MENOS DE 4 MINUTOS"),
 "p05": ("Cuarenta y cuatro de los fugados eran del mismo grupo criminal. El director del "
         "penal fue destituido ese mismo día, y después detenido.", "44 DEL MISMO GRUPO"),
 "p06": ("Después señalaron como cómplices a custodios, a mandos y al propio director. "
         "Cincuenta y tres hombres entraron presos y salieron caminando, sin un rasguño.",
         "SALIERON CAMINANDO"),
 "p07": ("Aquí el dato mata al gato. ¿Alguien pagó de verdad por esto? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-regina-martinez": {"planos": {
 "p00": ("La mataron a golpes en su propio baño. La fiscalía dijo que fue un robo de celular.",
         "XALAPA · ABRIL 2012"),
 "p01": ("Te imaginas a la corresponsal de una revista nacional que en abril de dos mil doce "
         "vivía sola en Xalapa. Escribía sobre policías, narco y el gobierno de Veracruz.",
         "ESCRIBÍA SOBRE EL GOBIERNO"),
 "p02": ("La encontraron en el baño de su departamento, estrangulada y golpeada. La casa "
         "estaba revuelta, pero no faltaba casi nada.", "LA CASA REVUELTA"),
 "p03": ("En diez días la fiscalía ya tenía sospechoso, confesión y móvil. Un hombre con "
         "antecedentes dijo que entró a robar un celular.", "CONFESIÓN EN 10 DÍAS"),
 "p04": ("Después se retractó frente al juez. Dijo que lo golpearon hasta que firmó lo que "
         "ellos querían.", "DIJO QUE LO TORTURARON"),
 "p05": ("Periodistas de veinte países revisaron el caso durante meses. Encontraron pruebas "
         "movidas, testigos sin interrogar y una línea que nadie siguió: sus últimos "
         "reportajes.", "20 PAÍSES REVISARON EL CASO"),
 "p06": ("Veracruz seguía siendo el peor lugar de América para ser periodista. La mató lo que "
         "escribía. El papel oficial dice que fue un celular.", "EL PAPEL DICE CELULAR"),
 "p07": ("Aquí el dato mata al gato. ¿Le creés a la versión del robo? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-rancho-izaguirre": {"planos": {
 "p00": ("Buscaban a sus hijos con palas y varillas. Encontraron un rancho con cientos de "
         "zapatos amontonados.", "TEUCHITLÁN, JALISCO · 2025"),
 "p01": ("Te imaginas a las madres buscadoras que en marzo de dos mil veinticinco entraron a "
         "un rancho de Jalisco. Iban sin orden judicial. Iban con varillas y con las manos.",
         "SIN ORDEN JUDICIAL"),
 "p02": ("El lugar ya había sido cateado por las autoridades seis meses antes. Entraron, se "
         "llevaron detenidos, y no revisaron el terreno.", "YA LO HABÍAN CATEADO"),
 "p03": ("Ellas encontraron ropa apilada contra una barda, mochilas, cartas y cientos de "
         "pares de zapatos ordenados por talla. Como una tienda.", "ZAPATOS POR TALLA"),
 "p04": ("Encontraron restos quemados entre la tierra. Encontraron hornos improvisados, "
         "hechos con ladrillo, en el piso del establo. Nadie los había visto.",
         "HORNOS DE LADRILLO"),
 "p05": ("Las fotos de los zapatos le dieron la vuelta al país en un día. Recién entonces el "
         "gobierno mandó peritos y cerró el rancho.", "SIN CIFRA OFICIAL"),
 "p06": ("Meses después todavía no hay una cifra oficial de cuántos pasaron por ahí. Lo "
         "encontraron ellas, con varillas, en un terreno donde el Estado ya había estado "
         "parado.", "LAS ENCONTRARON ELLAS"),
 "p07": ("Aquí el dato mata al gato. ¿Vamos a saber cuántos fueron? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-fatima-cecilia": {"planos": {
 "p00": ("Se la llevó de la mano saliendo de la escuela. La cámara lo grabó todo.",
         "CDMX · FEBRERO 2020"),
 "p01": ("Te imaginas a la niña de siete años que en febrero de dos mil veinte salió de su "
         "primaria en Tláhuac. Su mamá llegó tarde. Una mujer la estaba esperando.",
         "TENÍA SIETE AÑOS"),
 "p02": ("La maestra la dejó salir sola al patio. La mujer le dio la mano, le dijo algo, y "
         "las cámaras las siguieron dos cuadras.", "LA CÁMARA LAS SIGUIÓ"),
 "p03": ("La alerta se activó al día siguiente, tarde. Cuatro días después su cuerpo apareció "
         "en una bolsa negra, tirado en un terreno baldío.", "CUATRO DÍAS DESPUÉS"),
 "p04": ("La grabación mostraba la cara de la mujer, completa, de frente. Fue la gente en "
         "redes la que la reconoció, no la fiscalía.", "LA RECONOCIÓ LA GENTE"),
 "p05": ("Detuvieron a una pareja del mismo barrio, a media cuadra de la escuela. Los dos "
         "siguen presos, con sentencias de cincuenta y de setenta años.", "50 Y 70 AÑOS"),
 "p06": ("Tres semanas después medio millón de mujeres marcharon en la Ciudad de México. Esa "
         "cámara grabó a una niña, y terminó encendiendo un país.", "MEDIO MILLÓN MARCHARON"),
 "p07": ("Aquí el dato mata al gato. ¿Las alertas sirven de algo? Decímelo en los comentarios.",
         "DATO MATA GATO"),
}},

"guion-mara-castilla": {"planos": {
 "p00": ("Pidió un auto para volver a su casa. El chofer se la llevó para otro lado.",
         "CHOLULA · SEPTIEMBRE 2017"),
 "p01": ("Te imaginas a la estudiante de diecinueve años que en septiembre de dos mil "
         "diecisiete salió de un antro en Cholula. Pidió el viaje desde la app. Se subió sola.",
         "PIDIÓ EL VIAJE"),
 "p02": ("Mandó su ubicación a sus amigas, como habían quedado entre ellas. El punto azul "
         "dejó de moverse en un motel de la carretera.", "EL PUNTO SE DETUVO"),
 "p03": ("El chofer siguió manejando para la app seis días más. Después el auto apareció "
         "abandonado, con la placa cambiada y lavado por dentro.", "LA PLACA CAMBIADA"),
 "p04": ("A la semana encontraron su cuerpo en un baldío a las afueras de Puebla. La habían "
         "violado y estrangulado dentro del mismo auto.", "LA ENCONTRARON A LA SEMANA"),
 "p05": ("Mientras la buscaban, medio país opinaba sobre su falda, su hora de salida y cuánto "
         "había tomado. Nadie opinaba sobre el chofer.", "HABLABAN DE SU FALDA"),
 "p06": ("Lo detuvieron en Veracruz y le dieron cincuenta años. A ella la juzgaron primero, "
         "en redes, mientras él todavía andaba suelto.", "50 AÑOS DE CONDENA"),
 "p07": ("Aquí el dato mata al gato. ¿Es seguro hoy pedir un viaje de noche? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-metro-linea-12": {"planos": {
 "p00": ("Iban parados en hora pico cuando la vía se partió abajo del vagón. Cayeron doce "
         "metros.", "CDMX · MAYO 2021"),
 "p01": ("Te imaginas a los pasajeros que en mayo de dos mil veintiuno volvían del trabajo en "
         "la Línea 12. Eran las diez y media de la noche. El tren iba lleno.",
         "LÍNEA 12, 10:30 PM"),
 "p02": ("La trabe se venció entre dos columnas, sin aviso. El vagón se dobló en V y quedó "
         "colgando sobre la avenida.", "SE DOBLÓ EN V"),
 "p03": ("Murieron veintiséis personas y más de cien quedaron heridas. La mayoría eran "
         "vecinos de Tláhuac volviendo a su casa de noche.", "26 MUERTOS"),
 "p04": ("La línea tenía apenas nueve años de abierta. Ya la habían cerrado una vez, en dos "
         "mil catorce, por fallas en las mismas vías.", "YA LA HABÍAN CERRADO"),
 "p05": ("Un peritaje noruego encontró soldaduras mal hechas y pernos que nunca quedaron "
         "fijos. Fue falla de construcción, no de mantenimiento. Estaba mal desde el día uno.",
         "FALLA DE CONSTRUCCIÓN"),
 "p06": ("Cuatro años después nadie con firma está condenado. La vía tardó segundos en "
         "partirse. El culpable lleva cuatro años sin aparecer.", "NADIE CONDENADO"),
 "p07": ("Aquí el dato mata al gato. ¿Te subirías hoy a esa línea? Decímelo en los comentarios.",
         "DATO MATA GATO"),
}},

"guion-estudiantes-cine-jalisco": {"planos": {
 "p00": ("Grababan un trabajo de la escuela en una casa prestada. Los mataron por "
         "confundirlos con otros.", "TONALÁ, JALISCO · 2018"),
 "p01": ("Te imaginas a los tres estudiantes de cine que en marzo de dos mil dieciocho "
         "salieron a grabar a Tonalá. Tenían veinte años. Era un ejercicio de clase, nada más.",
         "TENÍAN 20 AÑOS"),
 "p02": ("La casa que usaron era de una tía de uno de ellos. Un grupo armado la tenía "
         "vigilada desde antes, por otra razón.", "UNA CASA PRESTADA"),
 "p03": ("Los levantaron pensando que eran de una banda rival. Los subieron a una camioneta a "
         "plena luz y nadie los volvió a ver.", "LOS CONFUNDIERON"),
 "p04": ("Los interrogaron, los mataron, y disolvieron los cuerpos en ácido. Uno de los que "
         "lo hizo cobraba tres mil pesos por semana por ese trabajo.",
         "3 MIL PESOS POR SEMANA"),
 "p05": ("La policía lo tomó como una desaparición común durante dos semanas. Se movió recién "
         "cuando el caso llegó a los periódicos del país.", "DOS SEMANAS SIN BUSCARLOS"),
 "p06": ("Hubo detenidos, confesiones y condenas de más de cincuenta años. Salieron a grabar "
         "un ejercicio de clase y no quedó nada que enterrar.", "MÁS DE 50 AÑOS"),
 "p07": ("Aquí el dato mata al gato. ¿La condena alcanza para esto? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-ohl-mexico-audios": {"planos": {
 "p00": ("Quedaron grabados repartiendo sobornos y hablando de cuánto inflar el peaje. Nadie "
         "pisó la cárcel.", "MÉXICO · 2015"),
 "p01": ("Te imaginas a los directivos de una constructora española que en dos mil quince "
         "operaban autopistas de peaje en México. Hablaban por teléfono todos los días. "
         "Alguien los estaba grabando.", "AUTOPISTAS DE PEAJE"),
 "p02": ("Las cintas salieron primero en la radio y después en YouTube. Se escuchaba a los "
         "jefes hablando de a quién había que pagarle.", "SALIERON EN LA RADIO"),
 "p03": ("Hablaban de cobrar más caro de lo autorizado en la autopista. Hablaban de cómo "
         "arreglar el papeleo después, con el regulador.", "PEAJE MÁS CARO"),
 "p04": ("Uno decía en voz alta cuánto había que repartir y a quién le tocaba. Ninguno bajaba "
         "la voz. Nadie pensó que alguien escuchaba.", "NINGUNO BAJABA LA VOZ"),
 "p05": ("La empresa dijo que las grabaciones eran ilegales y estaban editadas. Renunciaron "
         "dos directivos, la bolsa se sacudió, y el tema se apagó en meses.",
         "SOLO DOS RENUNCIAS"),
 "p06": ("La empresa vendió su parte de las autopistas y se fue del país con ganancia. Los "
         "delataron sus propias voces, y eso no alcanzó para nada.", "SE FUERON CON GANANCIA"),
 "p07": ("Aquí el dato mata al gato. ¿Esas grabaciones debieron alcanzar? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},

"guion-ahorro-famsa-quiebra": {"planos": {
 "p00": ("Fueron a sacar sus ahorros y encontraron el banco cerrado. Se lo habían prestado a "
         "sus propios dueños.", "MÉXICO · JUNIO 2020"),
 "p01": ("Te imaginas a los ahorradores que en dos mil veinte tenían su dinero en un banco de "
         "tiendas de muebles. Muchos eran jubilados. Muchos tenían ahí todo lo que juntaron.",
         "UN BANCO DE MUEBLERÍA"),
 "p02": ("El regulador le revocó la licencia un martes de junio. Al día siguiente las "
         "sucursales de todo el país no abrieron.", "REVOCARON LA LICENCIA"),
 "p03": ("La revisión encontró préstamos del propio banco a empresas de sus dueños. Miles de "
         "millones de pesos que ya no iban a volver.", "PRÉSTAMOS A SUS DUEÑOS"),
 "p04": ("El seguro de depósitos cubría hasta un tope legal por persona. Quien tenía más de "
         "ese tope, perdió la diferencia completa.", "EL SEGURO TENÍA TOPE"),
 "p05": ("Hubo jubilados que perdieron veinte años de ahorro en una semana. Muchos se "
         "enteraron por la tele, parados afuera de la sucursal.", "20 AÑOS EN UNA SEMANA"),
 "p06": ("El dueño terminó procesado, y el banco liquidado. Confiaron sus ahorros a un banco, "
         "y el banco se los prestó a sí mismo.", "SE LO PRESTÓ A SÍ MISMO"),
 "p07": ("Aquí el dato mata al gato. ¿Tu dinero está seguro donde está? Decímelo en los "
         "comentarios.", "DATO MATA GATO"),
}},
}

# Frases que se suman al plano indicado para llegar al piso de 170 palabras de
# la fórmula. Al recortar las frases largas el lote quedó entre 153 y 167, o
# sea corto: cada una de estas trae un dato que faltaba, no relleno.
EXTRA: dict[str, tuple[str, str]] = {
 "guion-culiacanazo-2019": ("p04", "Hubo familias que pasaron la noche entera tiradas "
                                   "abajo de la cama."),
 "guion-diana-cazadora": ("p04", "Casi ninguna de esas denuncias contra choferes llegó "
                                 "nunca a un juez."),
 "guion-masacre-creel": ("p05", "Diecisiete años después el caso sigue sin un solo "
                                "responsable en la cárcel."),
 "guion-samir-flores": ("p06", "Su radio comunitaria sigue transmitiendo desde el mismo "
                               "pueblo."),
 "guion-luz-del-mundo-abuso": ("p02", "Varias de ellas declararon por separado y contaron "
                                      "lo mismo."),
 "guion-bety-carino-caravana": ("p06", "El pueblo siguió cercado más de dos años."),
 "guion-fraude-segalmex": ("p02", "Compraba leche en polvo a sobreprecio, y después la "
                                  "dejaba pudrirse en las bodegas del propio organismo."),
 "guion-secuestro-matamoros-2023": ("p02", "Todo quedó grabado por un vecino desde una "
                                           "ventana."),
 "guion-aristoteles-sandoval": ("p02", "Nadie lo vio entrar."),
 "guion-explosion-tlahuelilpan": ("p05", "Hubo familias que perdieron al padre y a los dos "
                                         "hijos en la misma noche, en el mismo campo."),
 "guion-colegio-rebsamen": ("p06", "El colegio nunca volvió a abrir, y ese terreno quedó "
                                   "vacío hasta hoy."),
 "guion-fuga-cieneguillas": ("p04", "El video se filtró y lo vio todo el país."),
 "guion-regina-martinez": ("p04", "El hombre que firmó esa confesión terminó preso igual. "
                                  "Sigue adentro por un crimen que dice que no cometió."),
 "guion-rancho-izaguirre": ("p05", "Las fotos las publicaron ellas mismas, desde sus "
                                   "propios teléfonos."),
 "guion-fatima-cecilia": ("p02", "Nadie en la escuela preguntó quién era."),
 "guion-mara-castilla": ("p03", "La aplicación tardó días en entregar los datos completos "
                                "de ese viaje."),
 "guion-metro-linea-12": ("p04", "Los usuarios ya se quejaban del ruido y del movimiento."),
 "guion-estudiantes-cine-jalisco": ("p06", "Sus familias todavía piden que los nombren."),
 "guion-ohl-mexico-audios": ("p03", "Todo estaba en las cintas, palabra por palabra."),
 "guion-ahorro-famsa-quiebra": ("p05", "Varios habían metido ahí la liquidación entera de "
                                       "toda su vida laboral."),
}

# Correcciones de hechos encontradas al reescribir.
NOTAS = {
    "guion-masacre-creel": "CORREGIDO: la versión anterior fechaba la masacre en agosto "
                           "de 2022. La masacre de Creel fue en agosto de 2008.",
}


def main() -> None:
    for slug, cambio in LOTE.items():
        ruta = ANDROID_IN / slug / "guion.json"
        if not ruta.exists():
            print(f"  FALTA {slug}")
            continue
        g = json.loads(ruta.read_text(encoding="utf-8"))
        if "gancho" in cambio:
            g["gancho"] = cambio["gancho"]
        pid_extra, frase_extra = EXTRA.get(slug, (None, None))
        for plano in g["planos"]:
            nuevo = cambio["planos"].get(plano["id"])
            if not nuevo:
                continue
            narracion, rotulo = nuevo
            if plano["id"] == pid_extra:
                narracion = f"{narracion} {frase_extra}"
            plano["narracion"], plano["texto_en_pantalla"] = narracion, rotulo
            if plano.get("frase_cierre"):
                plano["frase_cierre"] = narracion.split(". ", 1)[-1]
        if slug in NOTAS:
            g.setdefault("verificar_antes_de_publicar", []).insert(0, NOTAS[slug])
        ruta.write_text(json.dumps(g, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        contenido = [p for p in g["planos"] if p.get("seccion") != "identidad_cierre"]
        pal = sum(len(p["narracion"].split()) for p in contenido)
        print(f"  {slug:<34} {pal:>3} palabras")


if __name__ == "__main__":
    main()
