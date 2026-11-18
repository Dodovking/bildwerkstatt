using System.Diagnostics;
using System.IO.Compression;
using System.Net.Http.Headers;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Lumen;

public class Fenster : Form
{
    const string Repo = "Dodovking/bildwerkstatt";
    const int Port = 7861;
    static readonly string Adresse = $"http://127.0.0.1:{Port}";
    static readonly string Version = typeof(Fenster).Assembly.GetName().Version!.ToString(3);

    readonly string[] argumente;
    readonly WebView2 web = new() { Dock = DockStyle.Fill, DefaultBackgroundColor = Color.FromArgb(11, 13, 22) };
    readonly HttpClient http = new() { Timeout = TimeSpan.FromMinutes(30) };
    readonly string wurzel;
    readonly string exePfad = Environment.ProcessPath!;
    StreamWriter protokoll;
    Process server;
    bool einrichtungLaeuft;
    bool updateLaeuft;
    public Action NachEnde;

    string App => Path.Combine(wurzel, "app");
    string Umgebung => Path.Combine(wurzel, "umgebung");
    string Python => Path.Combine(Umgebung, "Scripts", "python.exe");
    string Uv => Path.Combine(wurzel, "werkzeuge", "uv.exe");
    string ProtokollPfad => Path.Combine(wurzel, "lumen.log");

    public Fenster(string[] args)
    {
        argumente = args;
        wurzel = OrdnerBestimmen();
        Directory.CreateDirectory(wurzel);
        protokoll = new StreamWriter(new FileStream(ProtokollPfad, FileMode.Append, FileAccess.Write, FileShare.ReadWrite), Encoding.UTF8) { AutoFlush = true };
        Log($"==== Lumen {Version} startet ({exePfad}) ====");
        http.DefaultRequestHeaders.UserAgent.Add(new ProductInfoHeaderValue("LumenStudio", Version));

        Text = "Lumen Studio";
        Icon = Icon.ExtractAssociatedIcon(exePfad);
        BackColor = Color.FromArgb(11, 13, 22);
        var flaeche = Screen.PrimaryScreen!.WorkingArea;
        Size = new Size(Math.Min(1640, flaeche.Width - 40), Math.Min(1020, flaeche.Height - 40));
        MinimumSize = new Size(1100, 700);
        StartPosition = FormStartPosition.CenterScreen;
        if (flaeche.Width < 1700) WindowState = FormWindowState.Maximized;
        Controls.Add(web);
        Shown += async (_, _) => await Starten();
        FormClosing += (_, _) => ServerStoppen();
    }

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        int an = 1;
        DwmSetWindowAttribute(Handle, 20, ref an, sizeof(int));
        SetProp(Handle, "LumenStudio", (IntPtr)1);
    }

    static string OrdnerBestimmen()
    {
        var merk = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Lumen", "ordner.txt");
        var env = Environment.GetEnvironmentVariable("LUMEN_ORDNER");
        if (!string.IsNullOrWhiteSpace(env)) return env;
        try { if (File.Exists(merk)) { var t = File.ReadAllText(merk).Trim(); if (t.Length > 0) return t; } } catch { }
        var ziel = Directory.Exists(@"E:\") ? @"E:\KI\BildWerkstatt"
            : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Lumen");
        try { Directory.CreateDirectory(Path.GetDirectoryName(merk)!); File.WriteAllText(merk, ziel); } catch { }
        return ziel;
    }

    void Log(string t)
    {
        try { protokoll?.WriteLine($"{DateTime.Now:yyyy-MM-dd HH:mm:ss} {t}"); } catch { }
    }

    // ---------- Start ----------

    async Task Starten()
    {
        if (InstallierenFallsNoetig()) return;
        AlteDateienAufraeumen();
        try
        {
            var umg = await CoreWebView2Environment.CreateAsync(null, Path.Combine(wurzel, "webview"));
            await web.EnsureCoreWebView2Async(umg);
        }
        catch (WebView2RuntimeNotFoundException)
        {
            if (MessageBox.Show("Für Lumen wird die „Microsoft Edge WebView2 Runtime“ benötigt.\nJetzt die Download-Seite öffnen?",
                    "Lumen Studio", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes)
                Oeffnen("https://go.microsoft.com/fwlink/p/?LinkId=2124703");
            Close();
            return;
        }
        var c = web.CoreWebView2;
        c.Settings.AreDevToolsEnabled = argumente.Contains("--entwickler");
        c.Settings.IsStatusBarEnabled = false;
        c.Settings.IsZoomControlEnabled = true;
        c.WebMessageReceived += (_, e) => Nachricht(e.WebMessageAsJson);
        c.NewWindowRequested += (_, e) => { e.Handled = true; Oeffnen(e.Uri); };
        c.NavigationStarting += (_, e) =>
        {
            if (e.Uri.StartsWith("http") && !e.Uri.StartsWith(Adresse)) { e.Cancel = true; Oeffnen(e.Uri); }
        };
        c.DownloadStarting += (_, e) =>
        {
            var ordner = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
            if (Directory.Exists(ordner)) e.ResultFilePath = Path.Combine(ordner, Path.GetFileName(e.ResultFilePath));
        };
        c.NavigateToString(Einrichtungsseite());
        await Task.Delay(400);
        await Vorbereiten();
    }

    async Task Vorbereiten()
    {
        if (einrichtungLaeuft) return;
        einrichtungLaeuft = true;
        try
        {
            Schritt("dateien", "Programmdateien werden vorbereitet …");
            await Task.Run(EngineEntpacken);
            await Task.Run(AlteServerBeenden);
            if (!await Task.Run(UmgebungAktuell))
            {
                Schritt("python", "KI-Bibliotheken werden installiert – beim ersten Start ca. 3 GB, das dauert ein paar Minuten …");
                await Task.Run(UmgebungEinrichten);
            }
            Schritt("start", "KI-Engine startet …");
            await ServerStarten();
            Schritt("fertig", "Fertig!");
            web.CoreWebView2.Navigate(Adresse + "/");
        }
        catch (Exception ex)
        {
            Log("FEHLER: " + ex);
            Senden(new JsonObject { ["typ"] = "fehler", ["text"] = ex.Message, ["log"] = ProtokollEnde() });
        }
        finally { einrichtungLaeuft = false; }
    }

    void Schritt(string id, string text, double? prozent = null, string detail = null)
    {
        Log($"[{id}] {text} {detail}");
        Senden(new JsonObject { ["typ"] = "schritt", ["id"] = id, ["text"] = text, ["prozent"] = prozent, ["detail"] = detail });
    }

    void Senden(JsonObject n)
    {
        if (IsDisposed) return;
        BeginInvoke(() => { try { web.CoreWebView2?.PostWebMessageAsJson(n.ToJsonString()); } catch { } });
    }

    static string Einrichtungsseite()
    {
        using var s = typeof(Fenster).Assembly.GetManifestResourceStream("einrichtung.html")!;
        using var r = new StreamReader(s);
        return r.ReadToEnd().Replace("{{VERSION}}", Version);
    }

    // ---------- Engine & Python ----------

    void EngineEntpacken()
    {
        using var s = typeof(Fenster).Assembly.GetManifestResourceStream("engine.zip")!;
        using var ms = new MemoryStream();
        s.CopyTo(ms);
        var hash = Convert.ToHexString(SHA256.HashData(ms.ToArray()));
        var marke = Path.Combine(App, ".paket");
        if (File.Exists(marke) && File.ReadAllText(marke).Trim() == hash && File.Exists(Path.Combine(App, "server.py"))) return;
        Log("Engine wird entpackt");
        if (Directory.Exists(App)) Directory.Delete(App, true);
        ms.Position = 0;
        ZipFile.ExtractToDirectory(ms, App, true);
        File.WriteAllText(marke, hash);
    }

    void AlteServerBeenden()
    {
        try
        {
            using var k = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
            k.PostAsync(Adresse + "/api/beenden", null).Wait();
            Thread.Sleep(1200);
        }
        catch { }
    }

    string AnforderungenHash() =>
        Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(App, "requirements.txt")))) + "|torch-2.9.1-cu128";

    bool UmgebungAktuell()
    {
        var marke = Path.Combine(Umgebung, ".lumen");
        return File.Exists(Python) && File.Exists(marke) && File.ReadAllText(marke).Trim() == AnforderungenHash();
    }

    void UmgebungEinrichten()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Uv)!);
        if (!File.Exists(Uv))
        {
            Schritt("python", "Paketverwaltung wird geladen …");
            var zip = Uv + ".zip";
            Laden("https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip", zip, null).Wait();
            ZipFile.ExtractToDirectory(zip, Path.GetDirectoryName(Uv)!, true);
            File.Delete(zip);
        }
        if (!File.Exists(Python))
        {
            Schritt("python", "Python 3.12 wird eingerichtet …");
            Ausfuehren(Uv, $"venv --python 3.12 \"{Umgebung}\"", "Python-Umgebung");
        }
        Schritt("python", "PyTorch für NVIDIA-Grafikkarten wird installiert (ca. 2,5 GB) …");
        Ausfuehren(Uv, $"pip install --python \"{Python}\" torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128", "PyTorch");
        Schritt("python", "Weitere KI-Bibliotheken werden installiert …");
        Ausfuehren(Uv, $"pip install --python \"{Python}\" -r \"{Path.Combine(App, "requirements.txt")}\"", "Bibliotheken");
        File.WriteAllText(Path.Combine(Umgebung, ".lumen"), AnforderungenHash());
    }

    void Ausfuehren(string datei, string arg, string was)
    {
        Log($"> {datei} {arg}");
        var psi = new ProcessStartInfo(datei, arg)
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8,
        };
        psi.Environment["UV_PYTHON_INSTALL_DIR"] = Path.Combine(wurzel, "python");
        psi.Environment["UV_CACHE_DIR"] = Path.Combine(wurzel, "uv-cache");
        psi.Environment["UV_NO_PROGRESS"] = "1";
        using var p = Process.Start(psi)!;
        void Zeile(string z)
        {
            if (string.IsNullOrWhiteSpace(z)) return;
            Log("  " + z);
            Senden(new JsonObject { ["typ"] = "zeile", ["text"] = z.Trim() });
        }
        p.OutputDataReceived += (_, e) => Zeile(e.Data);
        p.ErrorDataReceived += (_, e) => Zeile(e.Data);
        p.BeginOutputReadLine();
        p.BeginErrorReadLine();
        p.WaitForExit();
        if (p.ExitCode != 0) throw new Exception($"{was} konnte nicht installiert werden (Code {p.ExitCode}). Bitte Internetverbindung prüfen und erneut versuchen.");
    }

    async Task ServerStarten()
    {
        var psi = new ProcessStartInfo(Python, "-u server.py")
        {
            WorkingDirectory = App, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8,
        };
        psi.Environment["BW_BASIS"] = wurzel;
        psi.Environment["BW_KEIN_FENSTER"] = "1";
        psi.Environment["BW_LEERLAUF_S"] = "0";
        psi.Environment["BW_ELTERN_PID"] = Environment.ProcessId.ToString();
        psi.Environment["PYTHONUTF8"] = "1";
        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        server = Process.Start(psi)!;
        server.OutputDataReceived += (_, e) => { if (e.Data != null) Log("[engine] " + e.Data); };
        server.ErrorDataReceived += (_, e) => { if (e.Data != null) Log("[engine] " + e.Data); };
        server.BeginOutputReadLine();
        server.BeginErrorReadLine();
        using var k = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
        var ende = DateTime.Now.AddMinutes(3);
        while (DateTime.Now < ende)
        {
            if (server.HasExited) throw new Exception($"Die KI-Engine wurde unerwartet beendet (Code {server.ExitCode}).");
            try { if ((await k.GetAsync(Adresse + "/api/info")).IsSuccessStatusCode) return; } catch { }
            await Task.Delay(500);
        }
        throw new Exception("Die KI-Engine antwortet nicht.");
    }

    void ServerStoppen()
    {
        try { if (server is { HasExited: false }) server.Kill(true); } catch { }
    }

    string ProtokollEnde()
    {
        try
        {
            using var fs = new FileStream(ProtokollPfad, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var r = new StreamReader(fs);
            var z = r.ReadToEnd().Split('\n');
            return string.Join("\n", z.Skip(Math.Max(0, z.Length - 25)));
        }
        catch { return ""; }
    }

    // ---------- Nachrichten aus der Oberfläche ----------

    async void Nachricht(string json)
    {
        try
        {
            var n = JsonNode.Parse(json);
            switch ((string)n?["typ"])
            {
                case "bereit":
                    Senden(new JsonObject { ["typ"] = "host", ["version"] = Version, ["wurzel"] = wurzel, ["exe"] = exePfad });
                    await UpdatePruefen(false);
                    break;
                case "update-pruefen": await UpdatePruefen(true); break;
                case "update-installieren": await UpdateInstallieren(); break;
                case "protokoll": Oeffnen(ProtokollPfad); break;
                case "neu-versuchen": await Vorbereiten(); break;
                case "ordner": Oeffnen(wurzel); break;
            }
        }
        catch (Exception ex) { Log("Nachricht: " + ex.Message); }
    }

    static void Oeffnen(string ziel)
    {
        try { Process.Start(new ProcessStartInfo(ziel) { UseShellExecute = true }); } catch { }
    }

    // ---------- Update ----------

    record Release(string Tag, System.Version Ver, string ExeUrl, long Groesse, string ShaUrl, string Notizen);

    async Task<Release> NeuestesRelease()
    {
        var antwort = await http.GetAsync($"https://api.github.com/repos/{Repo}/releases/latest");
        if (antwort.StatusCode == System.Net.HttpStatusCode.NotFound) return null;
        antwort.EnsureSuccessStatusCode();
        var j = JsonNode.Parse(await antwort.Content.ReadAsStringAsync())!;
        var tag = (string)j["tag_name"] ?? "";
        if (!System.Version.TryParse(tag.TrimStart('v', 'V'), out var v)) return null;
        string exe = null, sha = null; long groesse = 0;
        foreach (var a in j["assets"]!.AsArray())
        {
            var name = (string)a!["name"];
            if (name == "Lumen.exe") { exe = (string)a["browser_download_url"]; groesse = (long)a["size"]!; }
            if (name == "Lumen.exe.sha256") sha = (string)a["browser_download_url"];
        }
        if (exe == null || sha == null) return null;
        return new Release(tag, v, exe, groesse, sha, (string)j["body"] ?? "");
    }

    async Task UpdatePruefen(bool zeigen)
    {
        var n = new JsonObject { ["typ"] = "update-info", ["aktuell"] = Version, ["zeigen"] = zeigen, ["verfuegbar"] = false };
        try
        {
            var r = await NeuestesRelease();
            if (r != null && r.Ver > System.Version.Parse(Version))
            {
                n["verfuegbar"] = true;
                n["neu"] = r.Ver.ToString(3);
                n["groesse_mb"] = Math.Round(r.Groesse / 1048576.0, 1);
                n["notizen"] = r.Notizen.Length > 1500 ? r.Notizen[..1500] + " …" : r.Notizen;
            }
        }
        catch (Exception ex)
        {
            Log("Update-Prüfung: " + ex.Message);
            if (zeigen) n["fehler"] = "Keine Verbindung zu GitHub möglich. Bitte später erneut versuchen.";
        }
        Senden(n);
    }

    async Task UpdateInstallieren()
    {
        if (updateLaeuft) return;
        updateLaeuft = true;
        var neu = Path.Combine(Path.GetDirectoryName(exePfad)!, "Lumen.neu.exe");
        try
        {
            var r = await NeuestesRelease() ?? throw new Exception("Kein Update gefunden.");
            var erwartet = (await http.GetStringAsync(r.ShaUrl)).Trim().Split(' ', '\t')[0].ToUpperInvariant();
            await Laden(r.ExeUrl, neu, (p, mb) => Senden(new JsonObject
            {
                ["typ"] = "update-fortschritt", ["prozent"] = Math.Round(p, 1), ["text"] = $"Lade Version {r.Ver.ToString(3)} herunter … {mb:0} MB",
            }));
            Senden(new JsonObject { ["typ"] = "update-fortschritt", ["prozent"] = 100, ["text"] = "Prüfe Download …" });
            string ist;
            using (var f = File.OpenRead(neu)) ist = Convert.ToHexString(await SHA256.HashDataAsync(f));
            if (ist != erwartet) throw new Exception("Der Download ist beschädigt (Prüfsumme stimmt nicht). Bitte erneut versuchen.");
            Senden(new JsonObject { ["typ"] = "update-fortschritt", ["prozent"] = 100, ["text"] = "Installiere und starte neu …" });
            Log($"Update {Version} -> {r.Ver}");
            ServerStoppen();
            var alt = Path.Combine(Path.GetDirectoryName(exePfad)!, "Lumen.alt.exe");
            if (File.Exists(alt)) File.Delete(alt);
            File.Move(exePfad, alt);
            File.Move(neu, exePfad);
            NachEnde = () => Process.Start(new ProcessStartInfo(exePfad, "--warten") { UseShellExecute = false });
            Close();
        }
        catch (Exception ex)
        {
            Log("Update: " + ex);
            try { if (File.Exists(neu)) File.Delete(neu); } catch { }
            Senden(new JsonObject { ["typ"] = "update-fehler", ["text"] = ex.Message });
            updateLaeuft = false;
        }
    }

    async Task Laden(string url, string ziel, Action<double, double> fortschritt)
    {
        using var antwort = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead);
        antwort.EnsureSuccessStatusCode();
        var gesamt = antwort.Content.Headers.ContentLength ?? 0;
        await using var quelle = await antwort.Content.ReadAsStreamAsync();
        await using var datei = File.Create(ziel);
        var puffer = new byte[1 << 16];
        long geladen = 0; var zuletzt = DateTime.MinValue;
        int n;
        while ((n = await quelle.ReadAsync(puffer)) > 0)
        {
            await datei.WriteAsync(puffer.AsMemory(0, n));
            geladen += n;
            if (fortschritt != null && (DateTime.Now - zuletzt).TotalMilliseconds > 200)
            {
                zuletzt = DateTime.Now;
                fortschritt(gesamt > 0 ? geladen * 100.0 / gesamt : 0, geladen / 1048576.0);
            }
        }
    }

    // ---------- Installation ----------

    bool InstallierenFallsNoetig()
    {
        if (argumente.Contains("--hier")) return false;
        var ziel = Path.Combine(wurzel, "Lumen.exe");
        if (string.Equals(Path.GetFullPath(exePfad), Path.GetFullPath(ziel), StringComparison.OrdinalIgnoreCase)) { Verknuepfungen(ziel); return false; }
        try
        {
            var vorhanden = File.Exists(ziel) ? FileVersionInfo.GetVersionInfo(ziel).FileVersion : null;
            if (vorhanden == null || System.Version.Parse(vorhanden) < System.Version.Parse(Version + ".0") || argumente.Contains("--neu"))
            {
                Log($"Installiere nach {ziel}");
                File.Copy(exePfad, ziel, true);
            }
            Verknuepfungen(ziel);
            NachEnde = () => Process.Start(new ProcessStartInfo(ziel, "--warten") { UseShellExecute = false, WorkingDirectory = wurzel });
            Close();
            return true;
        }
        catch (Exception ex)
        {
            Log("Installation: " + ex.Message);
            return false;
        }
    }

    void Verknuepfungen(string ziel)
    {
        try
        {
            var orte = new[] { Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Environment.GetFolderPath(Environment.SpecialFolder.Programs) };
            var t = Type.GetTypeFromProgID("WScript.Shell");
            if (t == null) return;
            dynamic shell = Activator.CreateInstance(t);
            foreach (var ort in orte)
            {
                var alt = Path.Combine(ort, "BildWerkstatt.lnk");
                if (File.Exists(alt)) File.Delete(alt);
                var pfad = Path.Combine(ort, "Lumen Studio.lnk");
                if (File.Exists(pfad)) continue;
                dynamic lnk = shell.CreateShortcut(pfad);
                lnk.TargetPath = ziel;
                lnk.WorkingDirectory = Path.GetDirectoryName(ziel);
                lnk.IconLocation = ziel + ",0";
                lnk.Description = "Lumen Studio – KI-Bilder, Emotes und Sticker lokal erstellen";
                lnk.Save();
            }
        }
        catch (Exception ex) { Log("Verknüpfung: " + ex.Message); }
    }

    void AlteDateienAufraeumen()
    {
        foreach (var name in new[] { "Lumen.alt.exe", "Lumen.neu.exe" })
        {
            var p = Path.Combine(Path.GetDirectoryName(exePfad)!, name);
            for (int i = 0; i < 10 && File.Exists(p); i++)
            {
                try { File.Delete(p); } catch { Thread.Sleep(300); }
            }
        }
    }

    // ---------- Fenster nach vorne holen ----------

    public static void VorhandenesZeigen()
    {
        EnumWindows((h, _) =>
        {
            if (GetProp(h, "LumenStudio") != IntPtr.Zero)
            {
                ShowWindow(h, 9);
                SetForegroundWindow(h);
                return false;
            }
            return true;
        }, IntPtr.Zero);
    }

    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr GetProp(IntPtr h, string name);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern bool SetProp(IntPtr h, string name, IntPtr wert);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr h, int attr, ref int wert, int groesse);
}
