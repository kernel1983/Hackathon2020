
const { app, BrowserWindow, ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const http = require('http')
const uuid = require('uuid/v4')
const shajs = require('sha.js')
const dgram = require('dgram')
const merkle = require('merkle')
const express = require('express')
const EC = require('elliptic').ec
const ec = new EC('p192')

const HOST = '0.0.0.0';

let mainWindow

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  mainWindow.loadFile('index.html')

  // Open the DevTools.
  mainWindow.webContents.openDevTools()

  mainWindow.on('closed', function () {
    mainWindow = null
  })

  ipcMain.on('folder_load', (event) => {
    if (root_folder_hash_from_blockchain) {
      var root_folder_meta = get_meta(root_folder_hash_from_blockchain)
      event.reply('file_added', root_folder_meta)
    } else {
      var root_folder_meta = {
        "type": "root_folder",
        "store_id": "",
        "items": {},
        "owner": "someone's public key"
      }
      root_folder_hash_from_blockchain = put_meta(root_folder_meta)
      fs.writeFileSync('data/root_folder', root_folder_hash_from_blockchain)
    }
  })

  ipcMain.on('file_add', (event, filename) => {
    console.log(filename)
    const fd = fs.openSync(filename, 'r')
    const stats = fs.fstatSync(fd)
    var filesize_left = stats.size
    var hashes = []
    var buffer = new Buffer.alloc(2 ** 20)
    while (true) {
      if (filesize_left > 2 ** 20) {
        filesize_left -= 2 ** 20
        fs.readSync(fd, buffer, 0, 2 ** 20)
        const sha256hash = shajs('sha256').update(buffer).digest('hex')
        fs.writeFileSync('data/blobs/' + sha256hash, buffer)
        hashes.push(sha256hash)
        console.log(sha256hash)
      } else {
        console.log(filesize_left)
        fs.readSync(fd, buffer, 0, filesize_left)
        const sha256hash = shajs('sha256').update(buffer.slice(0, filesize_left)).digest('hex')
        fs.writeFileSync('data/blobs/' + sha256hash, buffer.slice(0, filesize_left))
        hashes.push(sha256hash)
        console.log(sha256hash)
        break
      }
    }
    fs.closeSync(fd)

    var tree = merkle('sha256').sync(hashes)
    var file_meta = {
      'type': 'file',
      'filename': filename,
      'objects': hashes
    }
    const file_meta_hash = put_meta(file_meta)
    console.log(tree.root())
    console.log(tree.level(0))

    var root_folder_meta = get_meta(root_folder_hash_from_blockchain)
    root_folder_meta["items"][filename] = file_meta_hash
    root_folder_hash_from_blockchain = put_meta(root_folder_meta)
    if (fs.existsSync('data/root_folder')) {
      const t = new Date()
      fs.renameSync('data/root_folder', 'data/root_folder_' + t.getTime())
    }
    fs.writeFileSync('data/root_folder', root_folder_hash_from_blockchain)

    const data_in_json = JSON.stringify({
      message:{
        msgid: uuid(),
        sender: sender.getPublic().encode('hex'),
        receiver: '8c48e76e-1471-42e5-a2dd-9eb1347ded03',
        timestamp: (new Date()).getTime()/1000,
        type: 'file_store',
        root_folder: root_folder_hash_from_blockchain
      },
      signature: 's'
    })
    var request = http.request({
      host: '127.0.0.1',
      port: 8001,
      path: '/new_msg',
      method: 'POST',
      headers:{
        'content-type':'application/json',
        'content-length':data_in_json.length
      }
    }, function(res) {
      console.log("statusCode: ", res.statusCode)
      console.log("headers: ", res.headers)
      var _data=''
      res.on('data', function(chunk){
        _data += chunk
      })
      res.on('end', function(){
        console.log("\n--->>\nresult:", _data)
      })
    })
    request.write(data_in_json)
    request.end()

    event.reply('file_added', root_folder_meta)
  })

  ipcMain.on('file_retrive', (event, filename, file_meta_hash) => {
    console.log('file_retrive', filename, file_meta_hash)
    var file_meta = get_meta(file_meta_hash)

    const fd = fs.openSync(filename, 'w')
    // var hashes = []
    // var buffer = new Buffer.alloc(2 ** 20)
    for (var i in file_meta['objects']) {
      console.log(file_meta['objects'][i])
      const buffer = fs.readFileSync('data/' + file_meta['objects'][i])
      // const stats = fs.fstatSync(fd)
      // var filesize_left = stats.size

      // if (filesize_left > 2 ** 20) {
      // filesize_left -= 2 ** 20
      fs.writeSync(fd, buffer, 0, buffer.length)
      // }
    }
    fs.closeSync(fd)
  })

  ipcMain.on('chat_send', (event, content) => {
    console.log(content)
    const data_in_json = JSON.stringify({
      message:{
        msgid: uuid(),
        sender: sender.getPublic().encode('hex'),
        receiver: '2',
        timestamp: (new Date()).getTime()/1000,
        type: 'chat_msg',
        content: content
      },
      signature: 's'
    })
    var request = http.request({
      host: '127.0.0.1',
      port: 8001,
      path: '/new_msg',
      method: 'POST',
      headers:{
        'content-type':'application/json',
        'content-length':data_in_json.length
      }
    }, function(res) {
      console.log("statusCode: ", res.statusCode)
      console.log("headers: ", res.headers)
      var _data=''
      res.on('data', function(chunk){
        _data += chunk
      })
      res.on('end', function(){
        console.log("\n--->>\nresult:", _data)
      })
    })
    request.write(data_in_json)
    request.end()
  })

  ipcMain.on('chat_load', (event, content) => {
    console.log(content)
    var request = http.request({
      host: '127.0.0.1',
      port: 8001,
      path: '/get_chat?user_pk='+sender.getPublic().encode('hex'),
      method: 'GET',
    }, function(res) {
      console.log("statusCode: ", res.statusCode)
      console.log("headers: ", res.headers)
      var _data=''
      res.on('data', function(chunk){
        _data += chunk
      })
      res.on('end', function(){
        console.log("\n--->>\nresult:", _data)
        event.reply('chat_loaded', JSON.parse(_data))
      })
    })
    // request.write(data_in_json)
    request.end()
  })

  // var ws = require("nodejs-websocket")

  // var ws_server = ws.createServer(function (conn) {
  //     console.log("New connection")
  //     conn.on("text", function (str) {
  //         console.log("Received "+str)
  //         conn.sendText(str.toUpperCase()+"!!!")
  //     })
  //     conn.on("close", function (code, reason) {
  //         console.log("Connection closed")
  //     })
  // }).listen(1234)

}

var root_folder_hash_from_blockchain
if (fs.existsSync('data/root_folder')) {
  const root_folder_hash_buffer = fs.readFileSync('data/root_folder')
  root_folder_hash_from_blockchain = root_folder_hash_buffer.toString()
} else {
  root_folder_hash_from_blockchain = null
}

var sender
if (fs.existsSync('data/pirvate_key')) {
  const sk_string = fs.readFileSync('data/pirvate_key')
  console.log(sk_string.toString())
  sender = ec.keyFromPrivate(sk_string, 'hex')
}else{
  sender = ec.genKeyPair()
  fs.writeFileSync("data/pirvate_key", sender.getPrivate().toString())
}

app.on('ready', function () {
  // if (mainWindow === null) 
  createWindow()

  const web = express()
  const router = express.Router()
  router.use(function (req, res, next) {
    console.log('%s %s %s', req.method, req.url, req.header('Range')) //req.path
    next()
  })
  router.use(express.static(path.join(__dirname, 'data')))
  web.use('/static', router)
  // web.get('/', (req, res) => {
  //   res.send('Hello World')
  // })

  web.listen(2018, HOST)

  const udp = dgram.createSocket('udp4');
  udp.on('listening', function () {
    var address = udp.address();
    console.log('UDP Server listening on ' + address.address + ':' + address.port);
  });

  udp.on('message', function (message, remote) {
    console.log(remote.address + ':' + remote.port + ' - ' + message)
    udp.send(message, 0, message.length, remote.port, remote.address, function (err, bytes) {
      if (err) throw err;
      console.log('UDP message sent to ' + remote.address + ':' + remote.port)
      // udp.close();
    });
  });

  udp.bind(2019, HOST, function () {
    udp.setBroadcast(true)
  });
})

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', function () {
  if (mainWindow === null) createWindow()
})

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.


function get_meta(hash) {
  const meta_buffer = fs.readFileSync('data/metas/' + hash)
  const meta = JSON.parse(meta_buffer.toString())
  return meta
}

function put_meta(obj) {
  const meta_json = JSON.stringify(obj)
  const meta_hash = shajs('sha256').update(meta_json).digest('hex')
  fs.writeFileSync('data/metas/' + meta_hash, meta_json)
  console.log('meta_hash', meta_hash)
  console.log(obj)
  return meta_hash
}

