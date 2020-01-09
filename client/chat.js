// This file is required by the index.html file and will
// be executed in the renderer process for that window.
// No Node.js APIs are available in this process because
// `nodeIntegration` is turned off. Use `preload.js` to
// selectively enable features needed in the rendering
// process.
const { ipcRenderer } = require('electron')
const { dialog } = require('electron').remote

window.onload = () => {
    this.document.getElementById('file_select').onchange = function (evt) {
        for (i = 0; i < evt.target.files.length; i++) {
            console.log(evt.target.files[i].path)
            ipcRenderer.send('file_add', evt.target.files[i].path)
        }
    }

    // ipcRenderer.on('file_added', (event, data) => {
    //     // console.log(data)
    //     var root_meta = this.JSON.parse(data)
    //     var folder_ele = this.document.getElementById('folder')
    //     while (folder_ele.firstChild) folder_ele.removeChild(folder_ele.firstChild)

    //     for (var i in root_meta['items']) {
    //         var e = this.document.createElement('div')
    //         e.innerHTML = '<span>' + i + '</span> <a class="download">Download</a>'
    //         e.setAttribute('hash', root_meta['items'][i])
    //         folder_ele.appendChild(e)
    //     }
    //     console.log(root_meta)
    // })

    // var folder = document.getElementById('folder')
    // folder.addEventListener('click', (event) => {
    //     if(!event.target.classList.contains("download")){
    //         return
    //     }
    //     var hash = event.target.parentElement.getAttribute('hash')
    //     var filename = event.target.parentElement.firstChild.innerText
    //     console.log(hash)

    //     dialog.showSaveDialog({
    //         title: 'Save',
    //         defaultPath: filename
    //     }).then((ret) => {
    //         if (!ret.canceled) {
    //             ipcRenderer.send('file_retrive', ret.filePath, hash)
    //             console.log(ret.filePath)
    //         }
    //     })
    // })
    // ipcRenderer.send('folder_load')

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
        var msg = document.createElement('div')
        var msgid = data[1]['message']['msgid'];
        if (msgid in msg_got)
            return

        msg_got[msgid] = msg;
        msg.innerText = data[1]['message']['content']
        document.getElementById('box').appendChild(msg);
        console.log(data[1]['transaction']['content']);

        // ws.close();
    };

    ws.onclose = function (evt) {
        console.log('Connection closed.');
    };

    this.document.getElementById('send').onclick = function () {
        // var request = new XMLHttpRequest();
        // var content = document.getElementById('content');
        // request.open('GET', '/api/new_msg?content=' + content.value, true);

        // request.onload = function () {
        //     if (this.status >= 200 && this.status < 400) {
        //         // Success!
        //         var resp = this.response;
        //     } else {
        //         // We reached our target server, but it returned an error

        //     }
        // };

        // request.onerror = function () {
        //     // There was a connection error of some sort
        // };

        // request.send();
    }
}
