namespace Lumen;

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        using var sperre = new Mutex(false, "Lumen-Studio-Einzelinstanz");
        bool frei;
        try { frei = sperre.WaitOne(args.Contains("--warten") ? 20000 : 0); }
        catch (AbandonedMutexException) { frei = true; }
        if (!frei)
        {
            Fenster.VorhandenesZeigen();
            return;
        }
        ApplicationConfiguration.Initialize();
        var f = new Fenster(args);
        Application.Run(f);
        try { sperre.ReleaseMutex(); } catch { }
        f.NachEnde?.Invoke();
    }
}
