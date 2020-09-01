Java.perform(function () {
    var cn = "android.webkit.WebView";
    var clazz = Java.use(cn);
    var func = "evaluateJavascript";
    var overloads = clazz[func].overloads;
    for (var i in overloads) {
        if (overloads[i].hasOwnProperty('argumentTypes')) {
            var parameters = [];
            var curArgumentTypes = overloads[i].argumentTypes;
            var args = [];
            var argLog = '[';
            var value_parameters = "[";
            for (var j in curArgumentTypes) {
                var cName = curArgumentTypes[j].className;
                parameters.push(cName);
                argLog += "'(" + cName + ") ' + v" + j + ",";
                value_parameters += "v" + j + " ,";
                args.push('v' + j);
            }

            argLog += ']';
            value_parameters += "]";

            var script = "var ret = this." + func + '(' + args.join(',') + ") || '';\n"
                + "send('className:" + cn + ", method:" + func + ", parameters:'+JSON.stringify(" + value_parameters + "));\n"
                + "return ret;";
            args.push(script);
            clazz[func].overload.apply(this, parameters).implementation = Function.apply(null, args);
        }
    }

});


Java.perform(function () {
    var cn = "android.webkit.WebSettings";
    var clazz = Java.use(cn);
    var func = "setJavaScriptEnabled";
    var overloads = clazz[func].overloads;
    for (var i in overloads) {
        if (overloads[i].hasOwnProperty('argumentTypes')) {
            var parameters = [];
            var curArgumentTypes = overloads[i].argumentTypes;
            var args = [];
            var argLog = '[';
            var value_parameters = "[";
            for (var j in curArgumentTypes) {
                var cName = curArgumentTypes[j].className;
                parameters.push(cName);
                argLog += "'(" + cName + ") ' + v" + j + ",";
                value_parameters += "v" + j + " ,";
                args.push('v' + j);
            }

            argLog += ']';
            value_parameters += "]";

            var script = "var ret = this." + func + '(' + args.join(',') + ") || '';\n"
                + "send('className:" + cn + ", method:" + func + ", parameters:'+JSON.stringify(" + value_parameters + "));\n"
                + "return ret;";
            args.push(script);
            clazz[func].overload.apply(this, parameters).implementation = Function.apply(null, args);
        }
    }
});

Java.perform(function () {
    var cn = "android.webkit.WebView";
    var clazz = Java.use(cn);
    var func = "loadUrl";
    var overloads = clazz[func].overloads;
    for (var i in overloads) {
        if (overloads[i].hasOwnProperty('argumentTypes')) {
            var parameters = [];
            var curArgumentTypes = overloads[i].argumentTypes;
            var args = [];
            var argLog = '[';
            var value_parameters = "[";
            for (var j in curArgumentTypes) {
                var cName = curArgumentTypes[j].className;
                parameters.push(cName);
                argLog += "'(" + cName + ") ' + v" + j + ",";
                value_parameters += "v" + j + " ,";
                args.push('v' + j);
            }

            argLog += ']';
            value_parameters += "]";

            var script = "var ret = this." + func + '(' + args.join(',') + ") || '';\n"
                + "send('className:" + cn + ", method:" + func + ", parameters:'+JSON.stringify(" + value_parameters + "));\n"
                + "return ret;";
            args.push(script);
            clazz[func].overload.apply(this, parameters).implementation = Function.apply(null, args);
        }
    }

});
