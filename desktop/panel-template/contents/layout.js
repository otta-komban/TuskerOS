/*
 * TuskerOS optional dock template.
 *
 * Uses Plasma's supported desktop scripting API and built-in widgets.
 * This template adds a panel when explicitly selected by the user; it does
 * not delete or rewrite existing panels, launchers, or desktop containment.
 */

var plasma = getApiVersion(1);

var dock = new plasma.Panel();
dock.location = "bottom";
dock.alignment = "center";
dock.height = Math.round(gridUnit * 3);
dock.floating = true;

// Native app launcher; retain the default Kickoff configuration.
dock.addWidget("org.kde.plasma.kickoff");

// Native window/task switcher; no custom task model is introduced.
var tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("fill", false);
tasks.writeConfig("maxStripes", 1);
tasks.writeConfig("showOnlyCurrentDesktop", false);
tasks.writeConfig("showOnlyCurrentScreen", false);
