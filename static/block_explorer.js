$(document).ready(function () {
    $(".block_txns").click(function () {
        let anchor_id = $(this).attr('id');
        let block_number = anchor_id.split(/_/)[2];
        $.ajax({
            url: "/ajax/block_data/" + block_number,
            success: function (result) {
                transactions = result.transactions;
                const txn_viewer = $("#txn_viewer");
                txn_viewer.empty();
                var max_gas_used = 0;
                var max_priority = 0;
                for (let each in transactions) {
                    if (transactions[each].gas_used > max_gas_used) {
                        max_gas_used = transactions[each].gas_used;
                    }
                    if (transactions[each].priority > max_priority) {
                        max_priority = transactions[each].priority;
                    }
                }
                for (let tx in transactions) {
                    var $table = $('<table class="transaction"/>');
                    txn_viewer.append($table);

                    $table.append("<tr class=\"ui_div_highlight\"><td><span class=\"tx_details_label\">Hash</span></td><td align='right'><span class=\"tx_details_value\">" + transactions[tx].hash + "</span></td></tr>");
                    $table.append("<tr><td><span class=\"tx_details_label\">From</span></td><td align='right'><span class=\"tx_details_value\">" + transactions[tx].from + "</span></td></tr>");
                    $table.append("<tr class=\"ui_div_highlight\"><td><span class=\"tx_details_label\">To</span></td><td align='right'><span class=\"tx_details_value\">" + transactions[tx].to + "</span></td></tr>");
                    $table.append("<tr><td><span class=\"tx_details_label\">Amount</span></td><td align='right'><span class=\"tx_details_value\">" + transactions[tx].amount + "</span></td></tr>");
                    $table.append("<tr class=\"ui_div_highlight\"><td><span class=\"tx_details_label\">Priority</span></td><td align='right'><span class=\"tx_details_value\">" + transactions[tx].priority + "</span></td></tr>");
                    $table.append("<tr><td><span class=\"tx_details_label\">Gas Used</span></td><td align='right'><span class=\"tx_details_value\">" + transactions[tx].gas_used + "</span></td></tr>");
                }

            }
        })
    });
});