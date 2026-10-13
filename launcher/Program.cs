using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;

namespace UniAssistLauncher
{
    class Program
    {
        private static Process backendProcess = null;

        static void Main(string[] args)
        {
            try
            {
                Console.Title = "UniAssist Enterprise Platform";
                Console.ForegroundColor = ConsoleColor.Cyan;
                Console.WriteLine("==================================================================");
                Console.WriteLine("          UNIASSIST ENTERPRISE UNIVERSITY PLATFORM");
                Console.WriteLine("              Native Windows Application Launcher");
                Console.WriteLine("==================================================================");
                Console.ResetColor();
            }
            catch { }

            string projectRoot = AppDomain.CurrentDomain.BaseDirectory;
            // Handle if running from a subfolder like bin/Release
            if (!File.Exists(Path.Combine(projectRoot, "backend", "main.py")))
            {
                DirectoryInfo parentDir = Directory.GetParent(projectRoot);
                string parent = parentDir != null ? parentDir.FullName : null;
                while (parent != null && !File.Exists(Path.Combine(parent, "backend", "main.py")))
                {
                    parentDir = Directory.GetParent(parent);
                    parent = parentDir != null ? parentDir.FullName : null;
                }
                if (parent != null)
                {
                    projectRoot = parent;
                }
            }

            // 1. Locate Python Interpreter
            string pythonExe = Path.Combine(projectRoot, ".venv", "Scripts", "python.exe");
            if (!File.Exists(pythonExe))
            {
                pythonExe = Path.Combine(projectRoot, "venv", "Scripts", "python.exe");
            }
            if (!File.Exists(pythonExe))
            {
                pythonExe = "python.exe";
            }

            // 0. Ensure Ollama Local AI Daemon is Running
            EnsureOllamaRunning();

            Console.WriteLine("\n[1/3] Starting UniAssist backend service...");

            // Check if backend is already running on port 8000
            bool alreadyRunning = IsBackendAlive("http://127.0.0.1:8000/api/health");

            if (!alreadyRunning)
            {
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = pythonExe,
                    Arguments = "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000",
                    WorkingDirectory = projectRoot,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                };
                startInfo.EnvironmentVariables["PYTHONPATH"] = projectRoot;

                try
                {
                    backendProcess = Process.Start(startInfo);
                    AppDomain.CurrentDomain.ProcessExit += (s, e) => ShutdownBackend();
                    Console.CancelKeyPress += (s, e) => ShutdownBackend();
                }
                catch (Exception ex)
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine("[ERROR] Could not start backend: " + ex.Message);
                    Console.ResetColor();
                    Console.WriteLine("Press any key to exit...");
                    Console.ReadKey();
                    return;
                }

                // Wait for backend to be ready
                Console.Write("[2/3] Connecting to system services");
                int attempts = 0;
                bool isReady = false;
                while (attempts < 40)
                {
                    Thread.Sleep(500);
                    Console.Write(".");
                    if (IsBackendAlive("http://127.0.0.1:8000/api/health"))
                    {
                        isReady = true;
                        break;
                    }
                    attempts++;
                }

                if (!isReady)
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine("\n[ERROR] Backend service failed to respond within 20 seconds.");
                    Console.ResetColor();
                    Console.WriteLine("Press any key to exit...");
                    Console.ReadKey();
                    ShutdownBackend();
                    return;
                }

                Console.WriteLine(" Ready!");
                // Extra grace sleep for uvicorn static files mount
                Thread.Sleep(1000);
            }
            else
            {
                Console.WriteLine(" - Backend service is already active on port 8000.");
            }

            // 2. Launch in Native Application Window Mode (Frameless app window, no browser tabs/URL bar)
            Console.WriteLine("[3/3] Opening UniAssist Desktop Application Window...");
            string appUrl = "http://127.0.0.1:8000/";
            string browserPath = FindBrowser();

            string userProfileDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "UniAssist",
                "UserData"
            );
            try
            {
                if (!Directory.Exists(userProfileDir))
                {
                    Directory.CreateDirectory(userProfileDir);
                }
            }
            catch { }

            Process browserProcess = null;
            if (!string.IsNullOrEmpty(browserPath))
            {
                try
                {
                    string appArgs = string.Format("--app=\"{0}\" --new-window", appUrl);
                    browserProcess = Process.Start(new ProcessStartInfo
                    {
                        FileName = browserPath,
                        Arguments = appArgs,
                        UseShellExecute = true
                    });
                }
                catch (Exception ex)
                {
                    Console.WriteLine("[WARNING] Native window mode failed: " + ex.Message);
                    try
                    {
                        browserProcess = Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
                    }
                    catch { }
                }
            }
            else
            {
                try
                {
                    browserProcess = Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
                }
                catch { }
            }

            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("\n==================================================================");
            Console.WriteLine("  UniAssist Desktop Application is Running (Native App Mode)");
            Console.WriteLine("  Ollama Local AI (Llama 3.2): ACTIVE");
            Console.WriteLine("  Web UI: http://127.0.0.1:8000/");
            Console.WriteLine("  Keep this window open while using UniAssist.");
            Console.WriteLine("  Press [ENTER] or close this window to exit UniAssist.");
            Console.WriteLine("==================================================================");
            Console.ResetColor();

            // Keep backend alive until user presses ENTER or closes console
            try
            {
                Console.ReadLine();
            }
            catch
            {
                while (backendProcess != null && !backendProcess.HasExited)
                {
                    Thread.Sleep(1000);
                }
            }

            ShutdownBackend();
        }

        private static bool IsBackendAlive(string url)
        {
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Proxy = null; // Crucial: bypass system proxy for instant localhost check
                req.Timeout = 1500;
                req.Method = "GET";
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    return resp.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }

        private static string FindBrowser()
        {
            string[] candidates = new string[]
            {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Microsoft", "Edge", "Application", "msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Microsoft", "Edge", "Application", "msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Google", "Chrome", "Application", "chrome.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Google", "Chrome", "Application", "chrome.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Google", "Chrome", "Application", "chrome.exe"),
            };

            foreach (string path in candidates)
            {
                if (File.Exists(path))
                {
                    return path;
                }
            }
            return null;
        }

        private static Process ollamaProcess = null;

        private static void EnsureOllamaRunning()
        {
            try
            {
                if (IsBackendAlive("http://127.0.0.1:11434/api/tags"))
                {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("[Ollama AI] Local AI daemon is active (Llama 3.2 available).");
                    Console.ResetColor();
                    return;
                }

                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string ollamaExe = Path.Combine(localApp, "Programs", "Ollama", "ollama.exe");
                if (!File.Exists(ollamaExe))
                {
                    ollamaExe = "ollama.exe";
                }

                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = ollamaExe,
                    Arguments = "serve",
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                ollamaProcess = Process.Start(startInfo);
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("[Ollama AI] Started local AI engine in background (Llama 3.2 ready).");
                Console.ResetColor();
            }
            catch (Exception ex)
            {
                Console.WriteLine("[Ollama AI] Note: " + ex.Message);
            }
        }

        private static void ShutdownBackend()
        {
            if (backendProcess != null && !backendProcess.HasExited)
            {
                try
                {
                    backendProcess.Kill();
                }
                catch { }
            }
            if (ollamaProcess != null && !ollamaProcess.HasExited)
            {
                try
                {
                    ollamaProcess.Kill();
                }
                catch { }
            }
        }
    }
}
