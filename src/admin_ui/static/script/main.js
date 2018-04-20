
function clock() {
    return new Date().getTime() / 1000.;
}

function AdminUIModel() {
    this.playlists = ko.observableArray();
    this.contents = ko.observableArray();
    this.placements = ko.observableArray();
    this.wingTrims = ko.observableArray(['raised', 'flat']);
    
    var model = this;
    this.load = function(data) {
	$.each(data.playlists, function(i, e) {
	    var pl = new PlaylistModel();
	    pl.load(e);
	    model.playlists.push(pl);
	});
	$.each(data.contents, function(i, e) {
	    var c = new ContentModel();
	    c.load(e);
	    model.contents.push(c);
	});
	$.each(data.placements, function(i, e) {
	    var p = new PlacementModel();
	    p.load(e);
	    model.placements.push(p);
	});
    }

    this.setTrim = function(e) {
	CONN.send(JSON.stringify({action: 'set_trim', state: e}));
    }
}

function PlaylistModel() {
    this.name = ko.observable()

    this.load = function(data) {
	console.log(data);
	this.name(data.name);
    }

    this.play = function() {
	CONN.send(JSON.stringify({action: 'set_playlist', name: this.name(), duration: getDuration()}));
    }
}

function ContentModel() {
    this.name = ko.observable()

    this.load = function(data) {
	this.name(data.name);
    }

    this.play = function() {
	CONN.send(JSON.stringify({action: 'play_content', name: this.name(), duration: getDuration()}));
    }
}

function PlacementModel() {
    this.name = ko.observable();
    this.stretch = ko.observable();
    this.ix = ko.observable();
    
    this.load = function(data) {
	this.name(data.name);
	this.stretch(data.stretch);
	this.ix(data.ix);
    }

    this.set = function() {
	CONN.send(JSON.stringify({action: 'set_placement', ix: this.ix()}));
    }
}

function getDuration() {
    return $('#mins').val() * 60;
}


function init() {
    var that = this;

    var model = new AdminUIModel();
    ko.applyBindings(model);
    
    this.conn = new WebSocket('ws://' + window.location.host + '/socket');
    this.conn.onopen = function () {
    };
    this.conn.onclose = function() {
	connectionLost();
    };
    this.conn.onerror = function (error) {
        console.log('websocket error ' + error);
	connectionLost();	
    };
    this.conn.onmessage = function (e) {
	console.log('receiving msg');
        var data = JSON.parse(e.data);
	console.log(data);

	if (data.type == "init") {
	    model.load(data);
	}
    };
    CONN = this.conn;
    
    $('#stopall').click(function() {
	CONN.send(JSON.stringify({action: 'stop_all'}));
    });
    $('#stopcurrent').click(function() {
	CONN.send(JSON.stringify({action: 'stop_current'}));
    });
    bindButton('#flap', 'flap');
}

function bindButton(sel, id) {
    $(sel).mousedown(function() {
	buttonAction(id, true);
    });
    $(sel).on('touchstart', function() {
	buttonAction(id, true);
    });
    $(sel).mouseup(function() {
	buttonAction(id, false);
    });
    $(sel).on('touchend', function() {
	buttonAction(id, false);
    });
}

function connectionLost() {
    alert('connection to server lost; reload the page');
}

SESSION_ID = Math.floor(1000000000*Math.random());
function sendEvent(id, type, val) {
    CONN.send(JSON.stringify({action: 'interactive', sess: SESSION_ID, id: id, type: type, val: val}));
}

BUTTON_KEEPALIVES = {};
function buttonAction(id, pressed) {
    
    if (pressed) {
	sendEvent(id, 'button', true);
	BUTTON_KEEPALIVES[id] = setInterval(function() {
	    sendEvent(id, 'button-keepalive');
	}, 1000);
    } else {
	sendEvent(id, 'button', false);
	clearInterval(BUTTON_KEEPALIVES[id]);
    }
}
