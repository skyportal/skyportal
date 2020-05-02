for (let i = 0; i < toggle.labels.length; i++) {
    eval("obs" + i).visible = (toggle.active.includes(i));
    eval("obserr" + i).visible = (toggle.active.includes(i));
    eval("bin" + i).visible = (toggle.active.includes(i));
    eval("binerr" + i).visible = (toggle.active.includes(i));
}
