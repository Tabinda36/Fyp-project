// The Django templates rendered their markup directly in <body>; several style <body> as a flex container
// that centres its children. React mounts inside <div id="root">, so make that wrapper box-less while one
// of these pages is mounted. The template CSS itself stays verbatim.
export const ROOT_PASSTHROUGH = '\n#root { display: contents; }\n';
