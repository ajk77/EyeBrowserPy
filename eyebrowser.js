/*
eyebrowser.js 
version 2.1
package github.com/ajk77/EyeBrowserPy
Created by AndrewJKing.com|@andrewsjourney

This code stores the pixel location of html containers of interest. 
>Each container (e.g. a div) must have a known id or be part of a class so that they can be identified via jQuery.
>Container locations are returned as as a comma separated list of container_id, top edge, left edge, bottom edge, right edge, next_container_id, ...
>Optional, containers are only returned if they are displayed within the bounds of a larger container. This is recommended if many containers are scrolled off screen.
>For static containers that contain a scroll bar, the scroll position can be returned instead. 
>The browser must be full screen for pixel locations to be accurately mapped to the output stream of the eye tracking device.

TODO:
[] generalize the functions
[] create settings file for url settings

USAGE:
This is an example file. It will need to be customized for your interface. 

---LICENSE---
This file is part of EyeBrowserPy

EyeBrowserPy is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or 
any later version.

EyeBrowserPy is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EyeBrowserPy.  If not, see <https://www.gnu.org/licenses/>.
*/


$(document).ready(function () {
	/* 
	Bind events for when container locations should be returned	
	> Add scroll events to the sections of the interface that you are interested in tracking
	*/

    // lab, med, and vital
    $(".labbox").bind("scroll", function() {
        send_div_locations();
    });
    $(".half-vitmedbox").bind("scroll", function() {
        send_div_locations();
    });
    $(".medbox").bind("scroll", function() {
        send_div_locations();
    });

    // notes scroll
    $(".report").bind("scroll", function() {
        //note_tracking();
        note_scroll(this.id);
    });
    // note tabs change
    $('.nav-track').on('shown.bs.tab', function () {
        note_tracking();
    });
    // note selection change
    $('.tab-pane').on('shown.bs.tab', function () {
        note_tracking();
    });

});

// send timestamp when leaving or refreshing a patient page
window.onbeforeunload = function () {
    if(in_study){
        let curr_timestamp = Date.now();
        create_post(patient_id.toString(), curr_timestamp.toString(), '0', '0')
    }
};


function send_div_locations(){
	/*
	This function pull the div locations for each 
	*/
    // Save pixelmap as long as within study or in test (99) mode
    if(in_study){
        // variables
        var lab_window, vit_window, io_window, med_window;
        var curr_pixelmap = [];
        var curr_groups = [];
        // timestamp
        var curr_timestamp = Date.now();
        if (!(screen.width === window.innerWidth && (screen.height === (window.innerHeight + 1) || screen.height === window.innerHeight))){
            sendAlert("Please press F11 to go to full screen!");
            send_div_locations();
        }else {
            if (selection_screen) {
                create_post(patient_id.toString(), curr_timestamp.toString(), 'SelectionScreen,0,0,0,0', 'SelectionScreen,0,0,0,0');
            }else if (paused_study){
                create_post(patient_id.toString(), curr_timestamp.toString(), 'PausedScreen,0,0,0,0', 'PausedScreen,0,0,0,0');
            }else{
                if (first_view) {
                    curr_pixelmap.push('FirstView,0,0,0,0');
                }
                // Tracking window position
                $("#lab_tracking").each(function () {
                    lab_window = this.getBoundingClientRect();
                });
                $("#vit_tracking").each(function () {
                    vit_window = this.getBoundingClientRect();
                });
                $("#io_tracking").each(function () {
                    io_window = this.getBoundingClientRect();
                });
                $("#med_tracking").each(function () {
                    med_window = this.getBoundingClientRect();
                });
                // Lab positions
                $(".chartrow").each(function () {
                    var edges = this.getBoundingClientRect();
                    var curr_array = [this.id.replace(',', ''), Math.round(edges.top), Math.round(edges.left), Math.round(edges.bottom), Math.round(edges.right)];
                    if (curr_array[1] < lab_window.bottom && curr_array[3] > lab_window.top ){
                        // object top is < (above) window bottom and object bottom is > (below) window top
                        curr_pixelmap.push(curr_array);
                    }
                });
                // vital positions
                $(".vitalrow").each(function () {
                    var edges = this.getBoundingClientRect();
                    var curr_array = [this.id.replace(',', ''), Math.round(edges.top), Math.round(edges.left), Math.round(edges.bottom), Math.round(edges.right)];
                    if (curr_array[1] < vit_window.bottom && curr_array[3] > vit_window.top ){
                        // div top (1) is < (pixel count) view bottom (3) and div bottom (3) is > view top (1)
                        curr_pixelmap.push(curr_array);
                    }
                });
                // IO positions
                $(".iorow").each(function () {
                    var edges = this.getBoundingClientRect();
                    var curr_array = [this.id.replace(',', ''), Math.round(edges.top), Math.round(edges.left), Math.round(edges.bottom), Math.round(edges.right)];
                    if (curr_array[1] < io_window.bottom && curr_array[3] > io_window.top ){
                        // div top (1) is < (pixel count) view bottom (3) and div bottom (3) is > view top (1)
                        curr_pixelmap.push(curr_array);
                    }
                });
                // Med positions
                $(".medrow").each(function () {
                    var edges = this.getBoundingClientRect();
                    var curr_array = [this.id.replace(',', ''), Math.round(edges.top), Math.round(edges.left), Math.round(edges.bottom), Math.round(edges.right)];
                    if (curr_array[1] < med_window.bottom && curr_array[3] > med_window.top ){
                        // div top (1) is < (pixel count) view bottom (3) and div bottom (3) is > view top (1)
                        curr_pixelmap.push(curr_array);
                    }
                });
                // Lab group positions
                $(".lab-group").each(function () {
                    var edges = this.getBoundingClientRect();
                    var curr_array = [this.id.replace(',', ''), Math.round(edges.top), Math.round(edges.left), Math.round(edges.bottom), Math.round(edges.right)];
                    curr_groups.push(curr_array)
                });

                create_post(patient_id.toString(), curr_timestamp.toString(), curr_pixelmap.toString(), curr_groups.toString());
            }
        }
    }
}



// this function send the note name and window position on each note navigated to, as well as the note scroll position on each scroll
function note_tracking(){
    let curr_timestamp = Date.now();
    if(in_study){
        let curr_array = false;
        let active_note_type = 'none';
        // Find active tab
        $('.nav-track.active').each(function () {
            active_note_type = this.id;
        });
        // Find active note location
        $('.active.report.tab-pane').each(function () {
            let edges = this.getBoundingClientRect();
            let t = edges.top;
            let b = edges.bottom;
            if (edges.top > 0) {
                curr_array = [this.id, Math.round(t), Math.round(edges.left), Math.round(b),
                              Math.round(edges.right)];
            }
        });
        // Test if active note existed: post location and scroll, else, post note name and empty
        if (curr_array) {
            create_post(patient_id.toString(), '', curr_array.toString(), '');
            note_scroll(curr_array[0]);
        } else {
            curr_array = [active_note_type, 0, 0, 0, 0];
            create_post(patient_id.toString(), '', curr_array.toString(), '');
        }
    }
}

// this function send the note scroll position on each scroll
function note_scroll(curr_id){
    if(in_study){
        let scroll_top = $('#'+curr_id).scrollTop();
        if (scroll_top === null){scroll_top = 0}
        let curr_pixelmap = Date.now().toString() + ',' + scroll_top;
        create_post(patient_id.toString(), '', curr_pixelmap, '');
    }
}


// Creates post to save pixelmaps
function create_post(id, curr_timestamp, curr_pixelmap, curr_groups) {
    console.log("create post is working!"); // sanity check
    var csrf_token = getCookie('csrftoken');
    $.ajax({
        url : "http://127.0.0.1:8000/YOURURL/save_pixelmap/", // the endpoint
        type : "POST", // http method
        data : { csrfmiddlewaretoken: csrf_token, the_pixelmap : curr_pixelmap, the_timestamp : curr_timestamp, pat_id : id, the_groups : curr_groups  }, // data sent with the post request
        // handle a successful response
        success : function(msg) {
            console.log(msg); // another sanity check
        },
        // handle a non-successful response
        error : function(xhr,errmsg,err) {
           console.log(xhr.status + ": " + xhr.responseText); // provide a bit more info about the error to the console
        }
    });
    return false;
}

// Gets cookie from webpage
function getCookie(cname) {
    let name = cname + "=";
    let ca = document.cookie.split(';');
    for(let i=0; i<ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1);
        if (c.indexOf(name) === 0) return c.substring(name.length,c.length);
    }
    return "";
}
