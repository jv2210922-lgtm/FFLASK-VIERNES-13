#I
from flask import Flask,render_template,request
#Iniciar Flask
app = Flask(_name_)

respuestas = ([]
#creamos una ruta
@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("formulario" , methods=["GET" , "POST"])
def formulario ():
    if request.method=="POST":
        nombre ==request.form.get("nombre","").strip()
        mensaje==request.form.get("mensaje","").strip()

   if not nombre of not mensaje:
    nueva_respuesta = {
        "nombre":nombre,
        "mensaje":mensaje
    }     
respuestas.append(nueva_respuesta)


@app.route("/saludo/<nombre>")
def saludo(nombre):
    return f"hola!{nombre}"


