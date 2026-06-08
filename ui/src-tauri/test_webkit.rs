use tauri::Manager;
fn test(app: &mut tauri::App) {
    let win = app.get_webview_window("main").unwrap();
    let _ = win;
}
