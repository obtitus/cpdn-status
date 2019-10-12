var textStyle = {color: '#373737',
		 fontName: 'Arial', // fixme: 'Myriad Pro', Calibri, Helvetica, Arial, sans-serif;
		 fontSize: 16}

var control = getControl_wrapper('control_{{chart_id}}');
var chart = new google.visualization.ChartWrapper({
    'chartType': 'AreaChart',
    'containerId': 'chart_{{chart_id}}',
    'options': {
	'title': '{{title}}',
	'legend': { 'position': 'top', 'maxLines': 5, 'textStyle': textStyle},
        'hAxis': {'title': 'Date',  'titleTextStyle': textStyle},
	'vAxis': {'title': 'Number',  'titleTextStyle': textStyle},
        'isStacked': true,
        // 'explorer': {},
	'chartArea': {'left': "8%", 'width': "85%"},
	// Allow multiple simultaneous selections.
	'selectionMode': 'multiple',
	// Group selections by x-value.
	'aggregationTarget': 'category',
	'areaOpacity': 1,
	'focusTarget': 'category'
    }
});

var data = new google.visualization.DataTable();
var None = null;
data.addColumn('datetime', 'Date');

// test
data.addColumn({type:'string', role:'annotation'});
data.addColumn({type:'string', role:'annotationText'});

{%- for head in header: %}
data.addColumn('number', '{{head.replace('{title}', '')}}');
{%- endfor %}

data.addRows([
    {%- for ix in range(1, data|count): %}
    [new Date({{1000*data[ix][0]}}),
     {%- for e in data[ix][1:-1]: -%}
     {{e}},
     {%- endfor -%}
     {{data[ix][-1]}}]
    {%- if ix != data|count-1: -%}
    ,
    {%- endif -%}
    {%- endfor %}
]);

var dashboard = new google.visualization.Dashboard(
    document.getElementById('dashboard_{{chart_id}}'));

dashboard.bind(control, chart);
dashboard.draw(data, {'annotations':{1: {style: 'line'}}, 'displayAnnotations': true});
