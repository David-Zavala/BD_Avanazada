from flask import Flask, render_template, request, session, flash, redirect
import os, secrets
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
mysql = MySQL(app)

######
# Configuracion de la BD

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '666'
app.config['MYSQL_DB'] = 'FedPac'

app.secret_key = secrets.token_hex(16)

@app.route('/', methods=['GET'])
def index():
    cur = mysql.connection.cursor()
    #cursor.execute('CALL mostrarProductos()')
    cur.callproc('mostrarProductos')
    productos = cur.fetchall()
    cur.nextset()
    cur.close()
    return render_template('index.html', productos=productos)

@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/api/registrar', methods=['POST'])
def registrar():
    _name=request.form['username']
    _password=request.form['password']
    _email=request.form['correo']        
    _lastname=request.form['apellido']
    _birthDate=request.form['nacimiento']
    _country=request.form['pais']
    _mailAddress=request.form['direccion']
    _phone=request.form['phone']

    #usamos mariadb
    cursor=mysql.connection.cursor()
    #_password_hasheado=generate_password_hash(_password)

    #cursor.execute('CALL sacarNombre(%s)', (_name,))
    #cursor.execute('SELECT nombreUsuario FROM Usuarios WHERE nombreUsuario = %s', (_name,))
    cursor.callproc('sacarNombre',[_name])
    nombres = cursor.fetchall()
    cursor.nextset()
    if len(nombres) == 0: 
        cursor.callproc('registroUsuario',[_password, _name, _lastname, _email, _birthDate, _mailAddress, _country, _phone])
        cursor.nextset()
        cursor.callproc('sacarId',[_name])
        idUser = cursor.fetchone()[0]
        idUser = int(idUser)
        cursor.nextset()
        cursor.callproc('insertarCarritoNuevo',[idUser])
        cursor.connection.commit()
        cursor.close()
        return render_template('login.html', message='Registrado con exito, ahora haz login')
    else:
        cursor.close()
        return render_template('registro.html', error_message='Registro ya insertado')

@app.route('/login')
def iniciarSesion():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    cursor = mysql.connection.cursor()
    if request.method == "POST":
        _name=request.form['username']
        _password=request.form['password']
        
        #cursor.execute('CALL login(%s, %s, %s)', (_name, _password, finalResult,))
        cursor.callproc('login',[_name, _password])
        finalResult = cursor.fetchone()[0]
        cursor.nextset()
        
        #cursor.execute('CALL sacarId(%s)', (_name,))
        cursor.callproc('sacarId',[_name])
        idUsuario = cursor.fetchone()
        cursor.nextset()

        if finalResult == "1":
            session['username'] = _name
            session['idUser'] = idUsuario
            cursor.close()
            return redirect('/')
        else:
            cursor.close()
            return render_template('login.html',message='Usuario o Contraseña no existen')

@app.route('/cerrarSesion')
def cerrar_sesion():
    session.pop('username', None)
    session.pop('idUser', None)
    session.clear()
    return redirect('/')

@app.route('/productos')
def productos():
    cursor = mysql.connection.cursor()
    cursor.callproc('mostrarProductos')
    productos = cursor.fetchall()
    cursor.close()
    return render_template('productos.html', productos=productos)

@app.route('/mispedidos')
def mispedidos():
    cursor = mysql.connection.cursor()
    cursor.callproc('mostrarPedidos',[session['idUser']])
    pedidos = cursor.fetchall()
    cursor.nextset()
    cursor.callproc('sacarPedidosUsuario',[session['idUser']])
    productos = cursor.fetchall()
    cursor.close()
    return render_template('mispedidos.html', pedidos=pedidos, productos=productos)

@app.route('/error')
def error():
    return render_template('error.html') 

@app.route('/api/detalles/<int:producto_id>')
def detalles(producto_id):
    producto_id = int(producto_id)
    cursor = mysql.connection.cursor()
    cursor.callproc('mostrarDetalleProducto', [producto_id])
    producto = cursor.fetchall()
    cursor.nextset()
    cursor.close()
    return render_template('detallesproducto.html',producto=producto)

@app.route('/api/acarrito/<int:producto_id>', methods=['POST'])
def acarrito(producto_id):

    if 'idUser' in session:
        _cantidad = request.form['cantidad']
        cursor = mysql.connection.cursor()

        cursor.callproc('sacarCarrito', [session['idUser']])
        carrito_id = cursor.fetchone()[0]
        carrito_id = int(carrito_id)
        cursor.nextset()
        cursor.callproc('validarproductoCarrito', [producto_id])
        result = cursor.fetchone()[0]
        cursor.nextset()

        if result == "1": #ya existe
            cursor.callproc('sacarCantidadDeProducto', [carrito_id,producto_id])
            _cantidadAnterior = cursor.fetchone()[0]
            cursor.nextset()
            _cantidadAnterior = int(_cantidadAnterior)
            _cantidad = int(_cantidad)
            total = _cantidad + _cantidadAnterior
            if total > 5:
                total = 5
            cursor.callproc('agregarCantidad', [total, carrito_id, producto_id])
            cursor.connection.commit()
            cursor.close()
        #AUMENTAR CANTIDAD
        else: # Si no existe:
            cursor.callproc('agregarProductoCarrito', [carrito_id,producto_id,_cantidad]) ##AQUI ME QUEDE
            cursor.connection.commit()
            cursor.close()
    return redirect('/productos')

@app.route('/carrito')
def carrito():
    cursor = mysql.connection.cursor()
    cursor.callproc('sacarProductosCarrito', [session['idUser']])
    productos = cursor.fetchall()
    cursor.nextset()
    cursor.close()
    return render_template('carrito.html', productos=productos)

@app.route('/pagar')
def pagar():
    cursor = mysql.connection.cursor()
    cursor.callproc('sacarIdProductos', [session['idUser']])
    ids = cursor.fetchall()
    cursor.nextset()
    cursor.callproc('crearPedido', [session['idUser']])
    pedido_id = cursor.fetchone()[0]
    pedido_id = int(pedido_id)
    cursro.nextset()
    for ide in ids:
        cursor.callproc('insertarProductosPedidos', [pedido_id, ide[0], ide[1]])
        cursor.nextset()
    cursor.callproc('borrarproductosCarrito', [session['idUser']])
    cursor.connection.commit()
    cursor.close()
    return redirect('/carrito')

@app.route('/api/actualizarCant/<int:producto_id>', methods=['POST'])
def actualizarCant(producto_id):
    cursor = mysql.connection.cursor()
    cantidad = request.form['cantidad']
    cantidad = int(cantidad)
    cursor.callproc('sacarIdCarrito', [session['idUser']])
    carrito_id = cursor.fetchone()[0]
    carrito_id = int(carrito_id)
    producto_id = int(producto_id)
    cursor.nextset()
    cursor.callproc('actualizarCarrito', [cantidad, carrito_id, producto_id])
    cursor.nextset()
    cursor.close()
    return redirect('/carrito')

@app.route('/api/borrarProdC/<int:producto_id>')
def borrarProdC(producto_id):
    cursor = mysql.connection.cursor()
    cursor.callproc('borrarProductoCarrito', [producto_id, session['idUser']])
    cursor.connection.commit()
    cursor.close()
    return redirect('/carrito')

@app.route('/admin')
def loginAdmin():
    return render_template('loginAdmin.html')

@app.route('/api/loginAdmin', methods=['POST'])
def inicarSesionAdmin():
    cursor = mysql.connection.cursor()
    if request.method == "POST":
        _idAdmin=request.form['username']
        _passwordAdmin=request.form['password']

        #cursor.execute('CALL login(%s, %s, %s)', (_name, _password, finalResult,))
        cursor.callproc('loginAdmin',[_idAdmin, _passwordAdmin])
        finalResult = cursor.fetchone()[0]
        cursor.nextset()

        if finalResult == "1":
            return redirect('/productosAdmin')
        else:
            cursor.close()
            return render_template('loginAdmin.html',message='Cuenta de administrador no existe')


@app.route('/productosAdmin')
def productosAdmin():
    cursor = mysql.connection.cursor()
    cursor.callproc('mostrarProductos')
    productos = cursor.fetchall()
    cursor.nextset()
    cursor.close()
    return render_template('productosAdmin.html', productos=productos)

@app.route('/adminAgregarProd')
def forma():
    return render_template('formaAgregarProd.html')

#agregar productos como ADMIN
@app.route('/api/adminAgregarProd', methods=['GET','POST'])
def formaAgregarProd():
    if request.method == 'GET':
        return render_template('error.html')
    if request.method == 'POST':
        nombre = request.form['username']
        desc = request.form['description']
        precio = request.form['price']
        foto = request.form['image']
        foto2 = 'static/images/' + foto
        cursor = mysql.connection.cursor()
        cursor.callproc('insertarProductos', [nombre, desc, precio, foto2])
        cursor.connection.commit()
        cursor.close()
        return redirect('/productosAdmin')

@app.route('/adminActualizarProd/<string:producto_id>')
def formaActualizar(producto_id):
    producto_id = int(producto_id)
    cursor = mysql.connection.cursor()
    cursor.callproc('mostrarDetalleProducto', [producto_id])
    productos = cursor.fetchall()
    cursor.nextset()
    cursor.close()
    return render_template('formaActualizarProd.html',producto=productos)

@app.route('/api/adminFormaActualizar/<string:producto_id>', methods=['POST'])
def apiFormaActualizar(producto_id):
    #Tomar todos los valores de la forma y actualizar los datos cambiados
    nombre = request.form['username']
    desc = request.form['description']
    precio = request.form['price']
    cursor = mysql.connection.cursor()
    productoid = int(producto_id)
    cursor.callproc('actualizarProductos', [nombre, desc, precio, productoid])
    cursor.connection.commit()
    cursor.close()
    return redirect('/productosAdmin')

@app.route('/cerrarSesionAdmin')
def cerrarSesionAdmin():
    return redirect('/')

@app.route('/pedidosAdmin')
def pedidosAdmin():
    cursor = mysql.connection.cursor()
    cursor.callproc('sacarPedidosAdmin')
    pedidos = cursor.fetchall()
    cursor.nextset()
    cursor.callproc('sacarProductosAdmin')
    productos = cursor.fetchall()
    cursor.nextset()
    return render_template('pedidosAdmin.html', pedidos=pedidos, productos=productos)

@app.route('/formaActualizarStatus/<string:id>')
def formaActualizarEstatis(id):
    pedid = int(id)
    cursor = mysql.connection.cursor()
    cursor.callproc('sacarPedidoAdminUnico',[pedid])
    pedidos = cursor.fetchall()
    cursor.nextset()
    cursor.callproc('sacarInformacionPedidoUnico',[pedid])
    productos = cursor.fetchall()
    cursor.nextset()
    cursor.close()
    return render_template('formaActualizarStatus.html',pedidos=pedidos,productos=productos)

@app.route('/api/adminActualizarStatus/<string:id>', methods=['POST']) #PEDIDO ID ??
def adminActualizarStatus(id):
    pedid = int(id)
    stat = request.form['status']
    adu = request.form['aduana']
    cursor = mysql.connection.cursor()
    cursor.callproc('validarAduana', [adu])
    result = cursor.fetchone()[0]
    cursor.nextset()
    if result == "1":
        cursor.callproc('sacarAduana', [adu])
        idAdu = cursor.fetchone()[0]
        cursor.nextset()
        cursor.callproc('cambiarStatus', [idAdu, stat, pedid])
        cursor.connection.commit()
        cursor.close
        return redirect('/pedidosAdmin')
    else:
        cursor.callproc('sacarPedidoAdminUnico',[pedid])
        pedidos = cursor.fetchall()
        cursor.nextset()
        cursor.callproc('sacarInformacionPedidoUnico',[pedid])
        productos = cursor.fetchall()
        cursor.nextset()
        cursor.close()
        return render_template('formaActualizarStatus.html',pedidos=pedidos,productos=productos,message='Esa aduana no existe')

if __name__ == '__main__':
    app.run(debug=True)














