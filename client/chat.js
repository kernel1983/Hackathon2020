// This file is required by the index.html file and will
// be executed in the renderer process for that window.
// No Node.js APIs are available in this process because
// `nodeIntegration` is turned off. Use `preload.js` to
// selectively enable features needed in the rendering
// process.
const { ipcRenderer } = require('electron')
const { dialog } = require('electron').remote

window.onload = () => {
    // this.document.getElementById('file_select').onchange = function (evt) {
    //     for (i = 0; i < evt.target.files.length; i++) {
    //         console.log(evt.target.files[i].path)
    //         ipcRenderer.send('file_add', evt.target.files[i].path)
    //     }
    // }

    var ws = new WebSocket('ws://127.0.0.1:8001/wait_msg');
    var msg_got = {};

    ws.onopen = function (evt) {
        console.log('Connection open ...');
        // ws.send('["Hello WebSockets!"]');
    };

    ws.onmessage = function (evt) {
        // console.log('Received Message: ' + evt.data);
        var data = JSON.parse(evt.data);
        console.log('Received Message: ' + data);
        var msgid = data[1]['message']['msgid'];
        if (msgid in msg_got)
            return

        var msg = document.createElement('div')
        msg_got[msgid] = msg
        msg.innerText = data[1]['message']['content']
        document.getElementById('box').appendChild(msg)
        console.log(data[1]['message']['content']);

        // ws.close();
    };

    ws.onclose = function (evt) {
        console.log('Connection closed.');
    };

    this.document.getElementById('send').onclick = function () {
        const content = document.getElementById('content')
        ipcRenderer.send('chat_send', content.value)
    }

    ipcRenderer.on('chat_loaded', (event, data) => {
        // console.log(data)
        var msgs = data['chat']
        var box_ele = this.document.getElementById('box')
        while (box_ele.firstChild) box_ele.removeChild(box_ele.firstChild)

        for (var i in msgs) {
            var msg = document.createElement('div')
            var msgid = msgs[i]['msgid'];
            msg_got[msgid] = msg
            msg.innerText = msgs[i]['content']
            box_ele.appendChild(msg)
        }
    })
    ipcRenderer.send('chat_load')
}
