from experta import *
from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDF, RDFS, XSD, FOAF, DCTERMS
import random
import re

from trabajo1_IA_fuzzy import evaluar_perfil_difuso


# Traducción de la ontología para traer los datos al sistema experto
g = Graph()
g.parse("ontologia_generada.ttl", format="turtle")
EX = Namespace("http://ejemplo.org/superheroes/")

# La función n_local toma un uri completo, a través de 
# la función split toma el nombre local y lo retorna 
def n_local(uri):
    return uri.split("/")[-1]

# Esta función toma un string le quita las tildes y le quita los espacios en blanco remplazandolos con una cadena vacia
def normalize(s):
    s = s.replace(" ", "").lower()
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
    )
    for a, b in replacements:
        s = s.replace(a, b)
    
    return s

clase=set()
propiedad=set()

# Agregamos los nombres de las clases y propiedades a sus sets respectivos 
for s,p,o in g.triples((None,RDF.type,RDFS.Class)):
    clase.add(n_local(s))

for s,p,o in g.triples((None,RDF.type,RDF.Property)) :
    s_literal=n_local(s)
    
    if "#" not in s_literal and ('/dc' not in s):
        propiedad.add(s_literal)


dict_personajes={}
# Este es el traductor de la ontología. 
# El primer ciclo for nos sirve para sacar los nombres de los personajes.
# El segundo ciclo for toma el uri del recurso y evalua las tripletas que tengan como sujeto al personajes obtenido en el primer ciclo for 
# 
# Ejm:
# Del primer for se obtiene el uri http://ejemplo.org/superheroes/SpiderMan, luego lee "SpiderMan" y si no se encuentra en dict_personajes, 
# lo agrega con un value que es un diccionario de la forma {'uri':'SpiderMan'}.

# El segundo for evalúa las tripletas que tengan sujeto http://ejemplo.org/superheroes/SpiderMan.

# Luego, el código evalúa que su predicado u objeto se encuentren en los sets propiedad y clase respectivamente (Como queremos obtener las clases y las propiedades de ese sujeto, es necesario
# mirar el predicado para una tripleta de propiedad y el objeto para una tripleta de clase).
# Posteriormente evalúa las restricciones y agrega esa propiedad o clase al diccionario de ese 
# personaje con value True si se encuentra asociado a este. ej. {Spiderman:{"uri":Spiderman, "name":Peter Parker, "tienePoder":True}}.
#Adicionalmente, las únicas clases/propiedades que sí guardan su instancia como value en el diccionario del personaje son: FOAF.name, EX.usaIdentidadOculta (qué también es boolean),
#EX.valorPopularidad, EX.valorAmenaza y EX.valorPoder.
# Por último, si el personaje no tiene alguna de las propiedades/clases, estas se instanciarán en el diccionario con un value Boolean(False)

for s,p,o in g.triples((None,RDF.type,EX.Personaje)):
    s_literal=n_local(s)
    if s_literal not in dict_personajes:
        dict_personajes[s_literal]={"uri": s_literal}

        for su,pe,ob in g.triples((s, None, None)):
            pe_literal=n_local(pe)
            ob_literal=n_local(ob)

            if pe_literal in clase.union(propiedad) or ob_literal in clase.union(propiedad):
                
                if isinstance(ob, Literal) and ob.datatype == XSD.integer:
                    dict_personajes[s_literal][pe_literal]= int(ob_literal)

                elif pe == FOAF.name:
                    dict_personajes[s_literal][pe_literal]=ob.value

                elif isinstance(ob, Literal) and ob.datatype == XSD.boolean:
                    dict_personajes[s_literal][pe_literal]=ob.value

                elif pe==RDF.type :dict_personajes[s_literal][ob_literal]= True 
                
                else: dict_personajes[s_literal][pe_literal]= True 

               
        for i in clase.union(propiedad):
            if str(i) not in dict_personajes[s_literal]:
                dict_personajes[s_literal][i] = False

# Aqui se tienen todas las preguntas posibles que el sistema de adivinanza puede hacer al usuario
preguntas_akinator=["¿Tú personaje es archienemigo de algún personaje de la lista? (Enemigo recurrente en series/películas)",
                    "¿Tú personaje es un villano Marvel?",
                    "¿Tú personaje es un villano DC?",
                    "¿Tú personaje es un humano Mutado? (Nació humano, pero adquirió poderes)",
                    "¿Tu personaje es un Superhéroe?",
                    "¿Tu personaje es un Supervillano?",
                    "¿Es un Héroe Marvel?",
                    "¿Es un Héroe DC?",
                    "¿Tu personaje es de especie Humano?",
                    "¿Es un humano tecnológico?  (Usa la tecnología a su favor)",
                    "¿Tu personaje es Alienígena? (No nació en la Tierra)",
                    "¿Tiene poder alguno? (Superfuerza, Supervelocidad, etc..)",
                    "¿Posee artefacto o equipo alguno (traje, arco, martillo, lazo, etc..)?",
                    "Tú personaje usa identidad oculta?"] 

clases_dic= {}
propiedades_dic={}
preguntas_procesadas=set()

# Este ciclo for recorre la union de ambos sets y asocia las propiedades/clase a su pregunta correspondiente 
for elemento in sorted(clase.union(propiedad),key=len,reverse=True): #agregue esto para que Humano no tuviera conflicto con otras preguntas 
    if elemento == 'Personaje': continue
    elemento_comparacion = elemento.lower()
    for pregunta in preguntas_akinator:
        pregunta_comparacion = normalize(pregunta)
        if pregunta in preguntas_procesadas: continue
        if elemento_comparacion in pregunta_comparacion:
            preguntas_procesadas.add(pregunta)
            if elemento in clase :clases_dic[elemento] = {"uri":elemento, "pregunta":pregunta}
            else: propiedades_dic[elemento]={"uri":elemento, "pregunta":pregunta}


# Clases de Hechos
class Personaje(Fact):
    """Candidato a ser el personaje a adivinar en la base de conocimientos"""
    pass

class Respuesta(Fact):
    """La respuesta actual dada por el usuario"""
    pass

class AtributoEvaluado(Fact):
    """Historial para no hacer las mismas preguntas"""
    pass

class EstadoJuego(Fact):
    """Control de fase de inferencia"""
    pass

class PerfilDifuso(Fact):
    """Almacena las métricas de desempate y dispara la regla difusas"""
    pass

class Clase(Fact):
    """Declara las clases de cada personaje"""
    pass
class Propiedad(Fact):
    """Declara las propiedades de cada personaje"""
    pass

# Sistema experto

class Akinator(KnowledgeEngine):

    
    
    @Rule(EstadoJuego(fase="descarte"), 
        OR(Clase(uri=MATCH.attr, pregunta=MATCH.p), Propiedad(uri=MATCH.attr, pregunta=MATCH.p)),
        NOT(AtributoEvaluado(nombre=MATCH.attr)),
        salience=5) 
    def descarte_preguntas(self, attr, p):
        print(p)
        respuesta=input("Sí (1) o No (0): ")
        self.declare(Respuesta(atributo=attr, valor=bool(int(respuesta))))


    @Rule(AS.r << Respuesta(atributo=MATCH.attr), AS.e << EstadoJuego(fase="descarte"), salience=7)
    def eliminiar_respuesta(self, r, e, attr):
        self.declare(AtributoEvaluado(nombre=attr))
        self.retract(r)
        candidatos_restantes = [fact for fact in self.facts.values() if isinstance(fact, Personaje)]
        for i in candidatos_restantes:
            print(i.items())
        if len(candidatos_restantes) <= 2:
            self.retract(e)
            self.declare(EstadoJuego(fase="final", candidatos=candidatos_restantes))
            

    # Dependiendo de la cantidad de los personajes restantes despues de la ronda de preguntas, el sistema tomara distintos caminos:
    # -Si solo queda un personaje el sistema lo imprimirá en pantalla automáticamente y el juego se dará por terminado 
    # -Si no queda ningún personaje en la lista se imprimirá en pantalla que no pudo adivinar el personaje
    # -Si quedan 2 personajes entrar en fase de desempate utilizando el sistema difuso para desempatar 
    @Rule(EstadoJuego(fase="final", candidatos=MATCH.candidatos_restantes),
           NOT(EstadoJuego(fase="desempate")),
           salience = 15)  # no-loop
    def decision_final(self, candidatos_restantes):
        if len(candidatos_restantes) == 1:
             cand = candidatos_restantes[0]
             print(f"\nEl motor determinó que es: {cand['uri'].upper()}")

        elif len(candidatos_restantes) == 0:
            print("\nNo se encontró un personaje con estos atributos ")

        elif len(candidatos_restantes) == 2:
             print(f"\nQuedan {len(candidatos_restantes)} candidatos. Activando lógica difusa...")
             self.declare(EstadoJuego(fase="desempate", candidatos=candidatos_restantes))
             try:
                       print("0-35: Débil (Humanos un poquito más poderosos)\n25-70: Medio poderoso (Armas avanzadas y sobrehumanos) \n60-100: Poderoso (Universal)")
                       v_pod = float(input("¿Nivel de PODER (0 a 100)?: \n"))
             
                       print("\nPiense en amenaza como, si el personaje fuera(o es) malo , que tanta magnitud destruiría")
                       print("0-3: Baja (Amenaza ciudades)\n3-7: Media (Amenaza el mundo)\n7-10: Alta (Amenaza el universo)")
                       v_ame = float(input("¿Nivel de AMENAZA (0 a 10)?: \n"))
             
             
                       print("\n0-30: Poco Popular \n30-70: Medio conocido \n70-100: ícono, muy conocido")
                       v_pop = float(input("¿Nivel de POPULARIDAD (0 a 100)?: \n"))             
                        #Se llama a la función evaluar_perfil_difuso y toma como parametros los valores ingresados por el usuario
                        #y se declara un hecho PerfilDifuso con el valor desfuzzificado de impacto esperado, el cual será utilizado en la regla de desempate
                       self.declare(PerfilDifuso(evaluar_perfil_difuso(v_pod, v_ame, v_pop)))
             
             
             except ValueError:
                    print("\nEntrada inválida. Ingresa solo números.")
             print(candidatos_restantes[0]["uri"])
             print(candidatos_restantes[1]["uri"
             ])

    @Rule(EstadoJuego(fase="desempate", candidatos=MATCH.candidatos_restantes),
          PerfilDifuso(impacto_esperado=MATCH.impacto_esperado))
    def desempate(self,candidatos_restantes, impacto_esperado):
        mejor_candidato = None
        menor_dif = float('inf')
        for cand in candidatos_restantes:
            # Extraemos los valores del Fact de Experta
            impacto_cand = evaluar_perfil_difuso(
                cand['valorPoder'],
                cand['valorAmenaza'],
                cand['valorPopularidad']
            )

            # El personaje que tenga la menor diferencia de impacto es el ganador
            if abs(impacto_esperado - impacto_cand) < menor_dif:
                menor_dif = abs(impacto_esperado - impacto_cand)
                mejor_candidato = cand

        if mejor_candidato:
            print(f"\nLa Lógica Difusa desempató a favor de: {mejor_candidato['uri'].upper()}\n")




    # REGLAS DE DESCARTE (Salience 10 - Se ejecutan antes de limpiar)

    @Rule(AS.r << Respuesta(atributo="Superheroe", valor=True), AS.c << Personaje(Superheroe=False), salience=10)
    def desc_no_superheroe(self, c):
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="VillanoDC"))
        self.declare(AtributoEvaluado(nombre="VillanoMarvel"))
        self.declare(AtributoEvaluado(nombre="Supervillano"))

    @Rule(Respuesta(atributo="Superheroe", valor=False), AS.c << Personaje(Superheroe=True), salience=10)
    def desc_si_superheroe(self, c): 
        self.retract(c)
        


    @Rule(Respuesta(atributo="Supervillano", valor=True), AS.c << Personaje(Supervillano=False), salience=10)
    def desc_no_supervillano(self, c): 
        self.retract(c)
        
               
        self.declare(AtributoEvaluado(nombre="Superheroe"))
        self.declare(AtributoEvaluado(nombre="HeroeMarvel"))
        self.declare(AtributoEvaluado(nombre="HeroeDC"))

    @Rule(Respuesta(atributo="Supervillano", valor=False), AS.c << Personaje(Supervillano=True), salience=10)
    def desc_si_supervillano(self, c): 
        self.retract(c)
        

    @Rule(Respuesta(atributo="HeroeMarvel", valor=True), AS.c << Personaje(HeroeMarvel=False), salience=10)
    def desc_no_hm(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="Supervillano"))
        self.declare(AtributoEvaluado(nombre="VillanoDC"))
        self.declare(AtributoEvaluado(nombre="VillanoMarvel"))
        self.declare(AtributoEvaluado(nombre="HeroeDC"))
        self.declare(AtributoEvaluado(nombre="Superheroe"))
        
    @Rule(Respuesta(atributo="HeroeMarvel", valor=False), AS.c << Personaje(HeroeMarvel=True), salience=10)
    def desc_si_hm(self, c): 
        self.retract(c)
        


    @Rule(Respuesta(atributo="HeroeDC", valor=True), AS.c << Personaje(HeroeDC=False), salience=10)
    def desc_no_hdc(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="Supervillano"))        
        self.declare(AtributoEvaluado(nombre="Superheroe"))
        self.declare(AtributoEvaluado(nombre="HeroeMarvel"))
        self.declare(AtributoEvaluado(nombre="VillanoMarvel"))
        self.declare(AtributoEvaluado(nombre="VillanoDC"))

    @Rule(Respuesta(atributo="HeroeDC", valor=False), AS.c << Personaje(HeroeDC=True), salience=10)
    def desc_si_hdc(self, c): 
        self.retract(c)
        


    @Rule(Respuesta(atributo="VillanoMarvel", valor=True), AS.c << Personaje(VillanoMarvel=False), salience=10)
    def desc_no_villanomarvel(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="Supervillano"))        
        self.declare(AtributoEvaluado(nombre="Superheroe"))
        self.declare(AtributoEvaluado(nombre="HeroeMarvel"))
        self.declare(AtributoEvaluado(nombre="HeroeDC"))
        self.declare(AtributoEvaluado(nombre="VillanoDC"))

    @Rule(Respuesta(atributo="VillanoMarvel", valor=False), AS.c << Personaje(VillanoMarvel=True), salience=10)
    def desc_si_villanomarvel(self, c): 
        self.retract(c)
        

    @Rule(Respuesta(atributo="VillanoDC", valor=True), AS.c << Personaje(VillanoDC=False), salience=10)
    def desc_no_villanodc(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="Supervillano"))        
        self.declare(AtributoEvaluado(nombre="Superheroe"))
        self.declare(AtributoEvaluado(nombre="HeroeMarvel"))
        self.declare(AtributoEvaluado(nombre="HeroeDC"))
        self.declare(AtributoEvaluado(nombre="VillanoMarvel"))
                
    @Rule(Respuesta(atributo="VillanoDC", valor=False), AS.c << Personaje(VillanoDC=True), salience=10)
    def desc_si_villanodc(self, c): 
        self.retract(c)
        



    @Rule(Respuesta(atributo="Humano", valor=True), AS.c << Personaje(Humano=False), salience=10)
    def desc_no_humano(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="Alienigena"))

    @Rule(Respuesta(atributo="Humano", valor=False), AS.c << Personaje(Humano=True), salience=10)
    def desc_si_humano(self, c): 
        self.retract(c)
        

        
    @Rule(Respuesta(atributo="HumanoTecnologico", valor=True), AS.c << Personaje(HumanoTecnologico=False), salience=10)
    def desc_no_htec(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="HumanoMutado"))
        self.declare(AtributoEvaluado(nombre="Alienigena"))
        self.declare(AtributoEvaluado(nombre="Humano"))

    @Rule(Respuesta(atributo="HumanoTecnologico", valor=False), AS.c << Personaje(HumanoTecnologico=True), salience=10)
    def desc_si_htec(self, c): 
        self.retract(c)
        


    @Rule(Respuesta(atributo="HumanoMutado", valor=True), AS.c << Personaje(HumanoMutado=False), salience=10)
    def desc_no_hmut(self, c): 
        self.retract(c)
        
        self.declare(AtributoEvaluado(nombre="HumanoTecnologico"))
        self.declare(AtributoEvaluado(nombre="Alienigena"))
        self.declare(AtributoEvaluado(nombre="Humano"))

    @Rule(Respuesta(atributo="HumanoMutado", valor=False), AS.c << Personaje(HumanoMutado=True), salience=10)
    def desc_si_hmut(self, c): 
        self.retract(c)
        


    @Rule(Respuesta(atributo="Alienigena", valor=True), AS.c << Personaje(Alienigena=False), salience=10)
    def desc_no_alien(self, c):
        self.retract(c)
                
        self.declare(AtributoEvaluado(nombre="Humano"))
        self.declare(AtributoEvaluado(nombre="HumanoTecnologico"))
            
    @Rule(Respuesta(atributo="Alienigena", valor=False), AS.c << Personaje(Alienigena=True), salience=10)
    def desc_si_alien(self, c): 
        self.retract(c)
              


    @Rule(Respuesta(atributo="tienePoder", valor=True), AS.c << Personaje(tienePoder=False), salience=10)
    def desc_no_poder(self, c): 
        self.retract(c)
        
    @Rule(Respuesta(atributo="tienePoder", valor=False), AS.c << Personaje(tienePoder=True), salience=10)
    def desc_si_poder(self, c): 
        self.retract(c)

    @Rule(Respuesta(atributo="poseeArtefacto", valor=True), AS.c << Personaje(poseeArtefacto=False), salience=10)
    def desc_no_art(self, c): 
        self.retract(c)

    @Rule(Respuesta(atributo="poseeArtefacto", valor=False), AS.c << Personaje(poseeArtefacto=True), salience=10)
    def desc_si_art(self, c): 
        self.retract(c)

    @Rule(Respuesta(atributo="esArchienemigoDe", valor=True), AS.c << Personaje(esArchienemigoDe=False), salience=10)
    def desc_no_archi(self, c): 
        self.retract(c)

    @Rule(Respuesta(atributo="esArchienemigoDe", valor=False), AS.c << Personaje(esArchienemigoDe=True), salience=10)
    def desc_si_archi(self, c): 
        self.retract(c)

    @Rule(Respuesta(atributo="usaIdentidadOculta", valor=True), AS.c << Personaje(usaIdentidadOculta=False), salience=10)
    def desc_no_identidad(self, c): 
        self.retract(c)

    @Rule(Respuesta(atributo="usaIdentidadOculta", valor=False), AS.c << Personaje(usaIdentidadOculta=True), salience=10)
    def desc_si_identidad(self, c): 
        self.retract(c)

# Personajes posibles y bienvenida al jugador 
print("Bienvenido a adivinaTron puedo adivinar cualquier superheroe/villano que este pensando")

idx = 1
for i in dict_personajes:
    print(f"{idx}. {i}")
    idx+=1
    
# Se instancia el motor de reglas
engine = Akinator()
engine.reset()

# Declaracion de hechos inciales Pesonajes, clases y propiedades 
hechos_iniciales=[]
for personaje in dict_personajes.values():
    hechos_iniciales.append(Personaje(**personaje))

for cla in clases_dic.values() :
    hechos_iniciales.append(Clase(**cla))

for pro in propiedades_dic.values():
    hechos_iniciales.append(Propiedad(**pro))
random.shuffle(hechos_iniciales)

for hecho in hechos_iniciales:
    engine.declare(hecho)


engine.declare(EstadoJuego(fase="descarte"))
engine.run()




