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

    ipcRenderer.on('file_added', (event, data) => {
        // console.log(data)
        var root_meta = this.JSON.parse(data)
        var folder_ele = this.document.getElementById('folder')
        while (folder_ele.firstChild) folder_ele.removeChild(folder_ele.firstChild)

        for (var i in root_meta['items']) {
            var e = this.document.createElement('div')
            e.innerHTML = '<span>' + i + '</span> <a class="download">Download</a>'
            e.setAttribute('hash', root_meta['items'][i])
            folder_ele.appendChild(e)
        }
        console.log(root_meta)
    })

    var folder = document.getElementById('folder')
    folder.addEventListener('click', (event) => {
        if(!event.target.classList.contains("download")){
            return
        }
        var hash = event.target.parentElement.getAttribute('hash')
        var filename = event.target.parentElement.firstChild.innerText
        console.log(hash)

        dialog.showSaveDialog({
            title: 'Save',
            defaultPath: filename
        }).then((ret) => {
            if (!ret.canceled) {
                ipcRenderer.send('file_retrive', ret.filePath, hash)
                console.log(ret.filePath)
            }
        })
    })
    ipcRenderer.send('folder_load')
}
