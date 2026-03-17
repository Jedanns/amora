#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

#[cfg(windows)]
mod job {
    use std::process::Child;
    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
    use windows_sys::Win32::System::JobObjects::*;

    pub struct JobObject {
        handle: HANDLE,
    }

    unsafe impl Send for JobObject {}
    unsafe impl Sync for JobObject {}

    impl JobObject {
        pub fn new() -> Option<Self> {
            unsafe {
                let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
                if handle.is_null() {
                    return None;
                }

                let mut info: JOBOBJECT_BASIC_LIMIT_INFORMATION = std::mem::zeroed();
                info.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

                let result = SetInformationJobObject(
                    handle,
                    JobObjectBasicLimitInformation,
                    &info as *const _ as *const _,
                    std::mem::size_of::<JOBOBJECT_BASIC_LIMIT_INFORMATION>() as u32,
                );

                if result == 0 {
                    CloseHandle(handle);
                    return None;
                }

                Some(JobObject { handle })
            }
        }

        pub fn assign_process(&self, child: &Child) {
            unsafe {
                use std::os::windows::io::AsRawHandle;
                let process_handle = child.as_raw_handle() as HANDLE;
                AssignProcessToJobObject(self.handle, process_handle);
            }
        }
    }

    impl Drop for JobObject {
        fn drop(&mut self) {
            unsafe {
                CloseHandle(self.handle);
            }
        }
    }
}

struct ManagedProcesses {
    backend: Mutex<Option<Child>>,
    koboldcpp: Mutex<Option<Child>>,
    #[cfg(windows)]
    _job: Option<job::JobObject>,
}

impl Drop for ManagedProcesses {
    fn drop(&mut self) {
        for (name, process) in [("backend", &self.backend), ("koboldcpp", &self.koboldcpp)] {
            if let Ok(mut guard) = process.lock() {
                if let Some(mut child) = guard.take() {
                    log::info!("Killing {} process (PID {})...", name, child.id());
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        }
    }
}

fn get_exe_dir() -> PathBuf {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."))
}

fn find_model_file(search_dir: &Path) -> Option<PathBuf> {
    let models_dir = search_dir.join("models");
    if models_dir.is_dir() {
        if let Ok(entries) = std::fs::read_dir(&models_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Some(ext) = path.extension() {
                    if ext == "gguf" {
                        return Some(path);
                    }
                }
            }
        }
    }
    None
}

fn spawn_backend(exe_dir: &Path) -> Option<Child> {
    let backend_exe = exe_dir.join("backend").join("backend.exe");
    if !backend_exe.exists() {
        log::warn!("Backend not found at: {}", backend_exe.display());
        return None;
    }

    let backend_dir = backend_exe.parent().unwrap();
    log::info!("Starting backend from: {}", backend_exe.display());

    match Command::new(&backend_exe)
        .current_dir(backend_dir)
        .creation_flags(0x08000000) // CREATE_NO_WINDOW
        .spawn()
    {
        Ok(child) => {
            log::info!("Backend started with PID: {}", child.id());
            Some(child)
        }
        Err(e) => {
            log::error!("Failed to start backend: {}", e);
            None
        }
    }
}

fn spawn_koboldcpp(exe_dir: &Path) -> Option<Child> {
    let kobold_exe = exe_dir.join("koboldcpp.exe");
    if !kobold_exe.exists() {
        log::warn!("KoboldCPP not found at: {}", kobold_exe.display());
        return None;
    }

    let model_file = find_model_file(exe_dir);
    let model_file = match model_file {
        Some(m) => m,
        None => {
            log::warn!("No .gguf model found in {}/models/", exe_dir.display());
            return None;
        }
    };

    log::info!("Starting KoboldCPP with model: {}", model_file.display());

    match Command::new(&kobold_exe)
        .current_dir(exe_dir)
        .args([
            "--model",
            model_file.to_str().unwrap_or(""),
            "--contextsize",
            "4096",
            "--port",
            "5001",
            "--gpulayers",
            "99",
            "--flashattention",
            "--threads",
            "8",
        ])
        .creation_flags(0x08000000) // CREATE_NO_WINDOW
        .spawn()
    {
        Ok(child) => {
            log::info!("KoboldCPP started with PID: {}", child.id());
            Some(child)
        }
        Err(e) => {
            log::error!("Failed to start KoboldCPP: {}", e);
            None
        }
    }
}

fn setup_file_logging(exe_dir: &Path) {
    let log_file = exe_dir.join("amora.log");
    if let Ok(file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_file)
    {
        let _ = fern::Dispatch::new()
            .format(|out, message, record| {
                out.finish(format_args!(
                    "[{}][{}] {}",
                    chrono::Local::now().format("%Y-%m-%d %H:%M:%S"),
                    record.level(),
                    message
                ))
            })
            .level(log::LevelFilter::Info)
            .chain(file)
            .apply();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let exe_dir = get_exe_dir();

            setup_file_logging(&exe_dir);
            log::info!("=== AMORA starting ===");
            log::info!("Exe directory: {}", exe_dir.display());

            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            app.handle()
                .plugin(tauri_plugin_updater::Builder::new().build())?;
            app.handle().plugin(tauri_plugin_process::init())?;

            #[cfg(windows)]
            let job_object = job::JobObject::new();
            #[cfg(windows)]
            if job_object.is_none() {
                log::warn!(
                    "Failed to create Windows Job Object - child processes may survive app exit"
                );
            }

            let koboldcpp_child = spawn_koboldcpp(&exe_dir);
            let backend_child = spawn_backend(&exe_dir);

            #[cfg(windows)]
            if let Some(ref job) = job_object {
                if let Some(ref child) = koboldcpp_child {
                    job.assign_process(child);
                    log::info!("KoboldCPP assigned to job object");
                }
                if let Some(ref child) = backend_child {
                    job.assign_process(child);
                    log::info!("Backend assigned to job object");
                }
            }

            app.manage(ManagedProcesses {
                backend: Mutex::new(backend_child),
                koboldcpp: Mutex::new(koboldcpp_child),
                #[cfg(windows)]
                _job: job_object,
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.try_state::<ManagedProcesses>() {
                    for (name, process) in
                        [("backend", &state.backend), ("koboldcpp", &state.koboldcpp)]
                    {
                        if let Ok(mut guard) = process.lock() {
                            if let Some(mut child) = guard.take() {
                                log::info!("Shutting down {} (PID {})...", name, child.id());
                                let _ = child.kill();
                                let _ = child.wait();
                                log::info!("{} terminated.", name);
                            }
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
