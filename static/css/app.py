
from flask import Flask,render_template,request
#Iniciar Flask
app = Flask(_name_)

respuestas = ()
#creamos una ruta
@app.route("/")
def inicio():
    return render_template("index.html")

@app.route







