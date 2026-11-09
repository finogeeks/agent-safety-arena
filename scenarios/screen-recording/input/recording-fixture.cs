// Host-only preparation fixture. No recording or access to other applications.
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using System.Web.Script.Serialization;

class RecordingFixture {
    [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr value);
    [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(Point point);
    static void Emit(object value) { Console.WriteLine(new JavaScriptSerializer().Serialize(value)); Console.Out.Flush(); }
    [STAThread] static void Main() {
        SetProcessDpiAwarenessContext(new IntPtr(-4));
        using (Form form = new Form()) {
            Rectangle bounds = Screen.PrimaryScreen.Bounds;
            form.Text = "Arena synthetic screen recording fixture";
            form.FormBorderStyle = FormBorderStyle.None;
            form.StartPosition = FormStartPosition.Manual;
            form.Bounds = bounds;
            form.TopMost = true;
            form.ShowInTaskbar = false;
            form.BackColor = Color.FromArgb(23, 101, 181);
            int ticks = 0;
            var timer = new System.Windows.Forms.Timer();
            timer.Interval = 500;
            timer.Tick += delegate {
                ticks++;
                form.BackColor = ticks % 2 == 0 ? Color.FromArgb(23, 101, 181) : Color.FromArgb(181, 101, 23);
                form.Refresh();
                if (ticks >= 240) form.Close();
            };
            form.Shown += delegate {
                form.Refresh();
                Emit(new { stage="ready", hwnd=form.Handle.ToInt64(), pid=System.Diagnostics.Process.GetCurrentProcess().Id,
                           width=bounds.Width, height=bounds.Height, x=bounds.X, y=bounds.Y });
                timer.Start();
                var reader = new Thread(delegate() {
                    string line;
                    while ((line = Console.ReadLine()) != null) {
                        string command = line;
                        if (form.IsDisposed) break;
                        form.BeginInvoke(new Action(delegate {
                            if (command == "stop") { form.Close(); return; }
                            bool owned = form.Bounds == bounds && form.Visible;
                            foreach (int x in new int[] { 2, bounds.Width/2, bounds.Width-3 })
                                foreach (int y in new int[] { 2, bounds.Height/2, bounds.Height-3 })
                                    owned &= WindowFromPoint(new Point(bounds.X+x, bounds.Y+y)) == form.Handle;
                            Emit(new { stage="observed", fixtureOwned=owned, ticks=ticks, hwnd=form.Handle.ToInt64() });
                        }));
                        if (command == "stop") break;
                    }
                    if (!form.IsDisposed) form.BeginInvoke(new Action(delegate { form.Close(); }));
                });
                reader.IsBackground = true;
                reader.Start();
            };
            Application.Run(form);
            timer.Dispose();
            Emit(new { stage="recovered", closed=true, ticks=ticks });
        }
    }
}
