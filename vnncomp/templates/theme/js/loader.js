function log_request(step_id) {
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

function refresh_output(ids, timers) {

    for (const id of ids) {
        log_request(id).then(ee => {
            $(`#${id}_logs`).text(`${ee.logs}`);
            $(`#${id}_results`).text(`${ee.results}`);
            $(`#${id}_status`).text(`${ee.status}`);
            $(`#${id}_note`).text(`Note: ${ee.note}`);


            timers[`${id}`].prevTime = ee.time;
            timers[`${id}`].element = $(`#${id}_time`);

            $(`#${id}_logs`).css("display", "block");
            $(`#${id}_results`).css("display", "block");
            $(`#${id}_time`).css("display", "block");

            // scroll at the bottom of log
            $(`#${id}_logs`).scrollTop(function() { return this.scrollHeight; });
            $(`#${id}_results`).scrollTop(function() { return this.scrollHeight; });
        })
    }

    setTimeout(() => refresh_output(ids, timers), 5000)
}

const TimerUpdater = function(element, prevTime) {
    this.prevTime = prevTime;
    this.element = element;

    this.calculateDiff = () => `last updated ${calcTimeDiff(this.prevTime)} ago`;
    this.timer_started = false

    var self = this;
    this.updater = () => {
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