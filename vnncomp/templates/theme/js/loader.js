function get_toolkit_task_step(step_id) {
    let settings = {
        "url": `/toolkit/details/step/${step_id}`,
        "method": "GET",
        "timeout": 0,
        "headers": {
            "Content-Type": "application/json",
        },
    };

    return $.ajax(settings).then(e => {
        // console.log(`pulled task ${step_id}`)
        return e
    });
}

function get_benchmark_task_step(step_id) {
    let settings = {
        "url": `/benchmark/details/step/${step_id}`,
        "method": "GET",
        "timeout": 0,
        "headers": {
            "Content-Type": "application/json",
        },
    };

    return $.ajax(settings).then(e => {
        // console.log(`pulled task ${step_id}`)
        return e
    });
}

function get_toolkit_task_status(task_id) {
    let settings = {
        "url": `/toolkit/details/task/${task_id}`,
        "method": "GET",
        "timeout": 0,
        "headers": {
            "Content-Type": "application/json",
        },
    };

    return $.ajax(settings).then(e => {
        // console.log(`pulled task ${step_id}`)
        return e
    });
}

function get_benchmark_task_status(task_id) {
    let settings = {
        "url": `/benchmark/details/task/${task_id}`,
        "method": "GET",
        "timeout": 0,
        "headers": {
            "Content-Type": "application/json",
        },
    };

    return $.ajax(settings).then(e => {
        // console.log(`pulled task ${step_id}`)
        return e
    });
}

function refresh_task_status(getter, task_id){
    getter(task_id).then(e => {
        if(e.output){
            // console.log(e)
            $("#task_status").text(`${e.done}`.toUpperCase())
            $("#task_output").html(e.output)
        } else {
            $("#task_status").text(e.error)
            $("#task_output").html(e.error)
        }
    })
    setTimeout(() => refresh_task_status(getter, task_id), 5000)
}

let refresh_output_called_once = false;
function refresh_task_steps(getter, ids, timers) {

    for (const id of ids) {
        getter(id).then(ee => {

            let logs_elem = new $$($(`#${id}_logs`));
            let results_elem = new $$($(`#${id}_results`));
            let status_elem = new $$($(`#${id}_status`));
            let note_elem = new $$($(`#${id}_note`));
            let time_elem = new $$($(`#${id}_time`));

            if(ee.logs.trim() === ""){
                logs_elem.hide();
            } else {
                if (! logs_elem.isVisible()) {
                    logs_elem.show();
                    logs_elem.it_should_scroll_to_bottom() // initially scroll at the bottom
                }
                else logs_elem.should_it_scroll_to_bottom()
            }

            if(ee.results.trim() === ""){
                results_elem.hide();
            } else {
                if (! results_elem.isVisible()) {
                    results_elem.show();
                    results_elem.it_should_scroll_to_bottom() // initially scroll at the bottom
                }
                else results_elem.should_it_scroll_to_bottom()
            }


            logs_elem.$.text(`${ee.logs}`);
            results_elem.$.text(`${ee.results}`);
            status_elem.$.html(`${ee.status}`);
            note_elem.$.html(`Note: ${ee.note}`);

            timers[`${id}`].prevTime = ee.time;
            timers[`${id}`].element = time_elem.$;


            if(! time_elem.isVisible())
                time_elem.show();

            if(ee.note.trim() === ""){
                note_elem.hide();
            } else {
                note_elem.show();
            }

            if( ee.status === "Done." || ee.status === "Aborted." ) {
                ids = ids.filter(e => e !== id)
                timers[`${id}`].stop_updating = true;
                time_elem.hide();
            }

            logs_elem.scroll_to_bottom_if_reminded();
            results_elem.scroll_to_bottom_if_reminded();

        })
    }

    refresh_output_called_once = true;
    setTimeout(() => refresh_task_steps(getter, ids, timers), 5000)
}

jQuery.prototype.scroll_to_bottom = function() {
    return this.scrollTop(this.prop("scrollHeight"));
}

String.prototype.trim = function() {
    return this.replace(/[\s\t\n]/g, "");
}

const $$ = function(elem){
    this.hide = () => elem.css("display", "none")
    this.show = () => elem.css("display", "block")
    this.isVisible = () => elem.css("display") === "block"
    this.scroll_to_bottom = () => elem.scroll_to_bottom()

    let should_scroll_to_bottom_reminder = false;
    this.should_it_scroll_to_bottom = () => {
        if (this.$.scrollTop() +
                    this.$.innerHeight() >=
                    this.$[0].scrollHeight)
            should_scroll_to_bottom_reminder = true;
        else
            should_scroll_to_bottom_reminder = false;
    }
    this.it_should_scroll_to_bottom = () => {
        should_scroll_to_bottom_reminder = true;
    }
    this.scroll_to_bottom_if_reminded = () => {
        if(should_scroll_to_bottom_reminder)
            this.scroll_to_bottom()
    }

    this.$ = elem
}

const TimerUpdater = function(element, prevTime) {
    this.prevTime = prevTime;
    this.element = element;

    this.calculateDiff = () => `last updated ${calcTimeDiff(this.prevTime)} ago`;
    this.timer_started = false

    this.stop_updating = false;

    var self = this;
    this.updater = () => {
        if(this.stop_updating) {
            new $$(self.element).hide();
            return
        }
        if(self.prevTime != null) {
            self.element.text(this.calculateDiff())
        }
        setTimeout(this.updater, 1000)
    }
}

function calcTimeDiff(prevTimeUTC){
    let prevTimeUTC_ = new Date(prevTimeUTC).getTime();
    let currentTimeUTC = new Date().getTime()

    return `${ Math.round((currentTimeUTC- prevTimeUTC_) / 1000 * (10) ) / 10 } seconds`
}