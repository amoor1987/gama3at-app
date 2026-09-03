import flet as ft
import sqlite3
import urllib.parse
import os
import shutil
from pathlib import Path
from fpdf import FPDF

def init_db():
    conn = sqlite3.connect("gama3at.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gama3at (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amount REAL,
            total_months INTEGER,
            start_month TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE gama3at ADD COLUMN start_month TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE gama3at ADD COLUMN total_members INTEGER")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gama3a_id INTEGER,
            name TEXT,
            phone1 TEXT,
            phone2 TEXT,
            shares REAL,
            roles TEXT
        )
    """)
    for col in [("phone1", "TEXT"), ("phone2", "TEXT"), ("shares", "REAL"), ("roles", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE members ADD COLUMN {col[0]} {col[1]}")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            month_name TEXT,
            status TEXT,
            FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "مدير الجمعيات الذكي"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20  # تم التعديل لتجنب الخطأ وتكون متوافقة 100% مع Flet
    page.scroll = ft.ScrollMode.AUTO

    init_db()

    current_view_state = ["home"]
    current_gama3a_info = [None, None]

    def handle_back_button(e=None):
        if current_view_state[0] == "details":
            home_view()
        else:
            def close_exit_dlg(ev):
                exit_dlg.open = False
                page.update()

            def confirm_exit(ev):
                page.window_close()

            exit_dlg = ft.AlertDialog(
                title=ft.Text("تأكيد الخروج"),
                content=ft.Text("هل تريد الخروج من البرنامج؟"),
                actions=[
                    ft.TextButton("لا", on_click=close_exit_dlg),
                    ft.ElevatedButton("نعم", bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, on_click=confirm_exit)
                ]
            )
            page.overlay.append(exit_dlg)
            exit_dlg.open = True
            page.update()

    page.on_back_press = handle_back_button

    def get_gama3at():
        conn = sqlite3.connect("gama3at.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, amount, total_months, start_month, total_members FROM gama3at")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def backup_database(e):
        try:
            downloads_path = str(Path.home() / "Downloads")
            if not os.path.exists(downloads_path):
                downloads_path = "."
                
            backup_file_name = "gama3at_backup.db"
            destination_path = os.path.join(downloads_path, backup_file_name)
            
            shutil.copy("gama3at.db", destination_path)
            
            def close_backup_dlg(ev):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("تم النسخ الاحتياطي بنجاح!"),
                content=ft.Text(f"تم حفظ النسخة في مجلد التنزيلات:\n{backup_file_name}"),
                actions=[ft.ElevatedButton("حسناً", on_click=close_backup_dlg)]
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        except Exception as ex:
            print(ex)

    def restore_database(e):
        def close_restore_dlg(ev):
            dlg.open = False
            page.update()

        downloads_path = str(Path.home() / "Downloads")
        backup_path_dl = os.path.join(downloads_path, "gama3at_backup.db")
        
        target_backup = backup_path_dl if os.path.exists(backup_path_dl) else "gama3at_backup.db"

        if os.path.exists(target_backup):
            shutil.copy(target_backup, "gama3at.db")
            dlg = ft.AlertDialog(
                title=ft.Text("تمت الاستعادة بنجاح!"),
                content=ft.Text("تم استعادة جميع البيانات من النسخة الاحتياطية. يرجى إعادة تشغيل التطبيق."),
                actions=[ft.ElevatedButton("حسناً", on_click=close_restore_dlg)]
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
            home_view()
        else:
            dlg = ft.AlertDialog(
                title=ft.Text("تنبيه"),
                content=ft.Text("لم يتم العثور على ملف نسخة احتياطية في مجلد التنزيلات."),
                actions=[ft.ElevatedButton("حسناً", on_click=close_restore_dlg)]
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

    def home_view():
        current_view_state[0] = "home"
        current_gama3a_info[0] = None
        current_gama3a_info[1] = None
        page.clean()
        
        # استخدام SafeArea عشان شريط الإشعارات العلوي ما يتدخلش في التصميم
        header = ft.SafeArea(
            ft.Row([
                ft.Icon(ft.Icons.SAVINGS, color=ft.Colors.GREEN, size=30),
                ft.Text("إدارة الجمعيات المالية", size=22, weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER)
        )

        backup_restore_row = ft.Row([
            ft.ElevatedButton("نسخ احتياطي للبيانات", icon=ft.Icons.BACKUP, bgcolor=ft.Colors.BLUE_GREY, color=ft.Colors.WHITE, on_click=backup_database),
            ft.ElevatedButton("استعادة البيانات", icon=ft.Icons.SETTINGS_BACKUP_RESTORE, bgcolor=ft.Colors.ORANGE, color=ft.Colors.WHITE, on_click=restore_database)
        ], alignment=ft.MainAxisAlignment.CENTER)

        gama3at_list = ft.Column(spacing=10)
        rows = get_gama3at()

        def open_add_gama3a(e):
            name_input = ft.TextField(label="اسم الجمعية (مثلاً: جمعية العيلة)")
            amount_input = ft.TextField(label="قيمة السهم الشهري", keyboard_type=ft.KeyboardType.NUMBER)
            members_count_input = ft.TextField(label="عدد الأعضاء", keyboard_type=ft.KeyboardType.NUMBER)
            
            months_list_dropdown = ft.Dropdown(
                label="شهر البداية",
                options=[
                    ft.dropdown.Option("يناير"), ft.dropdown.Option("فبراير"),
                    ft.dropdown.Option("مارس"), ft.dropdown.Option("إبريل"),
                    ft.dropdown.Option("مايو"), ft.dropdown.Option("يونيو"),
                    ft.dropdown.Option("يوليو"), ft.dropdown.Option("أغسطس"),
                    ft.dropdown.Option("سبتمبر"), ft.dropdown.Option("أكتوبر"),
                    ft.dropdown.Option("نوفمبر"), ft.dropdown.Option("ديسمبر")
                ],
                value="يناير"
            )
            year_input = ft.TextField(label="سنة البداية (مثلاً: 2026)", value="2026", keyboard_type=ft.KeyboardType.NUMBER)
            err_txt = ft.Text("", color=ft.Colors.RED)

            def close_dlg(e):
                dlg.open = False
                page.update()

            def save_gama3a(e):
                if name_input.value and amount_input.value and members_count_input.value:
                    try:
                        amt = float(amount_input.value)
                        mem_count = int(members_count_input.value)
                        total_m = mem_count
                        start_date_str = f"{months_list_dropdown.value} {year_input.value}"
                        
                        conn = sqlite3.connect("gama3at.db")
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO gama3at (name, amount, total_months, start_month, total_members) VALUES (?, ?, ?, ?, ?)",
                                       (name_input.value, amt, total_m, start_date_str, mem_count))
                        conn.commit()
                        conn.close()
                        dlg.open = False
                        page.update()
                        home_view()
                    except ValueError:
                        err_txt.value = "يرجى إدخال أرقام صحيحة لقيمة السهم وعدد الأعضاء."
                        page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("إنشاء جمعية جديدة"),
                content=ft.Column([name_input, amount_input, members_count_input, months_list_dropdown, year_input, err_txt], tight=True, scroll=ft.ScrollMode.AUTO),
                actions=[
                    ft.TextButton("إلغاء", on_click=close_dlg),
                    ft.ElevatedButton("حفظ", on_click=save_gama3a)
                ]
            )
            
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        if not rows:
            gama3at_list.controls.append(ft.Text("لا توجد جمعيات مسجلة حالياً. اضغط على زر الإضافة أدناه.", italic=True))
        else:
            for g in rows:
                g_id, g_name, g_amount, g_months, g_start, g_mem_count = g
                
                total_payout = g_amount * (g_mem_count or g_months or 1)

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.GROUP_WORK, color=ft.Colors.BLUE),
                                title=ft.Text(g_name, weight=ft.FontWeight.BOLD, size=16),
                                subtitle=ft.Text(f"السهم: {g_amount} ج.م | الشهور: {g_months} | إجمالي القبض: {total_payout} ج.م\nالبداية: {g_start or 'غير محدد'}"),
                            ),
                            ft.Row([
                                ft.TextButton("دخول الجمعية", icon=ft.Icons.ARROW_FORWARD, on_click=lambda e, gid=g_id, gname=g_name: gama3a_details_view(gid, gname))
                            ], alignment=ft.MainAxisAlignment.END)
                        ]),
                        padding=10
                    )
                )
                gama3at_list.controls.append(card)

        add_btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE), ft.Text("جمعية جديدة", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.GREEN,
            on_click=open_add_gama3a
        )

        footer_info = ft.Text("Design and Programming | Eng: Amr El-Sherif | N.O.: 01009191945", size=11, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER)

        page.add(header, backup_restore_row, ft.Divider(), gama3at_list, add_btn, ft.Divider(), footer_info)
        page.update()

    def gama3a_details_view(gama3a_id, gama3a_name):
        current_view_state[0] = "details"
        current_gama3a_info[0] = gama3a_id
        current_gama3a_info[1] = gama3a_name
        page.clean()

        conn = sqlite3.connect("gama3at.db")
        cursor = conn.cursor()
        cursor.execute("SELECT amount, total_months, start_month, total_members FROM gama3at WHERE id = ?", (gama3a_id,))
        g_info = cursor.fetchone()
        g_amount, g_months, g_start, g_mem_count = g_info if g_info else (0, 0, "", 12)
        max_allowed_months = g_mem_count if g_mem_count else g_months

        cursor.execute("SELECT id, name, phone1, phone2, shares, roles FROM members WHERE gama3a_id = ?", (gama3a_id,))
        rows = cursor.fetchall()
        conn.close()

        def generate_pdf(e):
            pdf = FPDF()
            pdf.add_page()
            
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Gama3at Report: {gama3a_name}", ln=True, align="C")
            
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 8, f"Share Amount: {g_amount} EGP | Total Months: {max_allowed_months} | Start: {g_start}", ln=True, align="C")
            pdf.ln(10)

            pdf.set_font("Arial", "B", 10)
            pdf.cell(50, 8, "Member Name", 1)
            pdf.cell(30, 8, "Phone", 1)
            pdf.cell(20, 8, "Shares", 1)
            pdf.cell(40, 8, "Months/Roles", 1)
            pdf.cell(30, 8, "Payment Status", 1, ln=True)

            pdf.set_font("Arial", "", 10)
            conn_db = sqlite3.connect("gama3at.db")
            cur = conn_db.cursor()
            for m in rows:
                m_id, m_name, p1, p2, shares, roles = m
                cur.execute("SELECT status FROM payments WHERE member_id = ? ORDER BY id DESC LIMIT 1", (m_id,))
                st = cur.fetchone()
                status_str = st[0] if st else "Not Paid"

                pdf.cell(50, 8, str(m_name), 1)
                pdf.cell(30, 8, str(p1 or ""), 1)
                pdf.cell(20, 8, str(shares), 1)
                pdf.cell(40, 8, str(roles or ""), 1)
                pdf.cell(30, 8, str(status_str), 1, ln=True)
            conn_db.close()

            pdf.ln(15)
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 6, "Design and Programming - Eng: Amr El-Sherif (N.O.: 01009191945)", ln=True, align="C")

            file_name = f"Report_{gama3a_name}.pdf"
            pdf.output(file_name)
            
            def close_pdf_dlg(ev):
                dlg_success.open = False
                page.update()

            dlg_success = ft.AlertDialog(
                title=ft.Text("تم إنشاء التقرير بنجاح!"),
                content=ft.Text(f"تم حفظ ملف الـ PDF باسم:\n{file_name}\nموجود في مجلد التنزيلات."),
                actions=[ft.ElevatedButton("حسناً", on_click=close_pdf_dlg)]
            )
            page.overlay.append(dlg_success)
            dlg_success.open = True
            page.update()

        def open_roles_guide(e):
            guide_dlg = ft.AlertDialog(
                title=ft.Text("دليل معرفة وحساب الأدوار"),
                content=ft.Text(f"نظام الأدوار يتم إدخاله يدوياً لكل عضو عبر أرقام الشهور (مثلاً: 1, 5). السيستم يتحقق تلقائياً من عدم تكرار نفس الشهر لأكثر من عضو، ويحذر إذا تجاوز الشهر عدد أشهر الجمعية الكلي ({max_allowed_months})."),
                actions=[ft.ElevatedButton("حسناً", on_click=lambda ev: close_g(guide_dlg))]
            )
            def close_g(d):
                d.open = False
                page.update()
            page.overlay.append(guide_dlg)
            guide_dlg.open = True
            page.update()

        header = ft.SafeArea(
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: home_view()),
                ft.Text(f"إدارة: {gama3a_name}", size=18, weight=ft.FontWeight.BOLD),
                ft.IconButton(icon=ft.Icons.HELP_OUTLINE, icon_color=ft.Colors.BLUE, tooltip="دليل الأدوار", on_click=open_roles_guide)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        pdf_btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.WHITE), ft.Text("طباعة تقرير الجمعية PDF", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.RED,
            on_click=generate_pdf
        )

        members_list = ft.Column(spacing=10)

        def open_add_member(e, member_data=None):
            is_edit = member_data is not None
            m_id = member_data[0] if is_edit else None

            name_in = ft.TextField(label="اسم العضو", value=member_data[1] if is_edit else "")
            p1_in = ft.TextField(label="رقم التليفون الأساسي", value=member_data[2] if is_edit else "", keyboard_type=ft.KeyboardType.PHONE)
            p2_in = ft.TextField(label="رقم التليفون الثاني (اختياري)", value=member_data[3] if is_edit else "", keyboard_type=ft.KeyboardType.PHONE)
            shares_in = ft.TextField(label="عدد الأسهم", value=str(member_data[4]) if is_edit else "1", keyboard_type=ft.KeyboardType.NUMBER)
            roles_in = ft.TextField(label=f"أشهر القبض (أقصى شهر {max_allowed_months}) - مثال: 1, 5", value=member_data[5] if is_edit else "", keyboard_type=ft.KeyboardType.TEXT)

            error_text = ft.Text("", color=ft.Colors.RED)

            def close_dlg(e):
                dlg.open = False
                page.update()

            def save_member(e):
                if not name_in.value:
                    error_text.value = "يرجى إدخال اسم العضو."
                    page.update()
                    return
                
                raw_roles = roles_in.value.replace("،", ",").split(",")
                new_roles = []
                for r in raw_roles:
                    r_clean = r.strip()
                    if r_clean.isdigit():
                        month_num = int(r_clean)
                        if month_num > max_allowed_months:
                            error_text.value = f"تحذير/خطأ: الشهر ({month_num}) يتجاوز عدد أشهر الجمعية الكلي ({max_allowed_months})!"
                            page.update()
                            return
                        new_roles.append(r_clean)

                if not new_roles:
                    error_text.value = "خطأ: يجب إدخال أرقام شهور صحيحة (مثل: 1, 2)"
                    page.update()
                    return

                conn = sqlite3.connect("gama3at.db")
                cursor = conn.cursor()
                if is_edit:
                    cursor.execute("SELECT roles FROM members WHERE gama3a_id = ? AND id != ?", (gama3a_id, m_id))
                else:
                    cursor.execute("SELECT roles FROM members WHERE gama3a_id = ?", (gama3a_id,))
                
                existing_roles = []
                for db_r in cursor.fetchall():
                    if db_r[0]:
                        existing_roles.extend([r.strip() for r in db_r[0].replace("،", ",").split(",") if r.strip()])
                
                for r in new_roles:
                    if r in existing_roles:
                        error_text.value = f"خطأ: الشهر رقم ({r}) محجوز بالفعل لعضو آخر!"
                        page.update()
                        conn.close()
                        return

                roles_str = ", ".join(new_roles)

                if is_edit:
                    cursor.execute("UPDATE members SET name=?, phone1=?, phone2=?, shares=?, roles=? WHERE id=?",
                                   (name_in.value, p1_in.value, p2_in.value, float(shares_in.value or 1), roles_str, m_id))
                else:
                    cursor.execute("INSERT INTO members (gama3a_id, name, phone1, phone2, shares, roles) VALUES (?, ?, ?, ?, ?, ?)",
                                   (gama3a_id, name_in.value, p1_in.value, p2_in.value, float(shares_in.value or 1), roles_str))
                
                conn.commit()
                conn.close()
                dlg.open = False
                page.update()
                gama3a_details_view(gama3a_id, gama3a_name)

            dlg = ft.AlertDialog(
                title=ft.Text("تعديل عضو" if is_edit else "إضافة عضو جديد للجمعية"),
                content=ft.Container(
                    content=ft.Column([name_in, p1_in, p2_in, shares_in, roles_in, error_text], tight=True, scroll=ft.ScrollMode.AUTO),
                    height=320
                ),
                actions=[
                    ft.TextButton("إلغاء", on_click=close_dlg),
                    ft.ElevatedButton("حفظ", on_click=save_member)
                ]
            )
            
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def delete_member(member_id):
            conn = sqlite3.connect("gama3at.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
            conn.commit()
            conn.close()
            gama3a_details_view(gama3a_id, gama3a_name)

        if not rows:
            members_list.controls.append(ft.Text("لم يتم إضافة أعضاء لهذه الجمعية بعد.", italic=True))
        else:
            for index, m in enumerate(rows):
                m_id, m_name, p1, p2, shares, roles = m

                def format_wa_phone(phone):
                    if not phone:
                        return ""
                    clean_p = phone.strip()
                    if clean_p.startswith("0"):
                        clean_p = clean_p[1:]
                    if not clean_p.startswith("+2"):
                        clean_p = "+20" + clean_p
                    return clean_p

                def send_wa(phone_num):
                    formatted_phone = format_wa_phone(phone_num)
                    if not formatted_phone:
                        return "#"
                    wa_msg = urllib.parse.quote(f"أهلاً يا أستاذ {m_name}، تذكير بميعاد قسط الجمعية للشهر الحالي. شكراً لحضرتك.")
                    return f"https://wa.me/{formatted_phone}?text={wa_msg}"

                wa_buttons = []
                if p1:
                    wa_buttons.append(ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.CHAT, color=ft.Colors.WHITE, size=14), ft.Text(f"واتس (1): {p1}", color=ft.Colors.WHITE, size=11)], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor=ft.Colors.GREEN,
                        url=send_wa(p1)
                    ))
                if p2:
                    wa_buttons.append(ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.CHAT, color=ft.Colors.WHITE, size=14), ft.Text(f"واتس (2): {p2}", color=ft.Colors.WHITE, size=11)], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor=ft.Colors.GREEN_700,
                        url=send_wa(p2)
                    ))

                conn = sqlite3.connect("gama3at.db")
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM payments WHERE member_id = ? ORDER BY id DESC LIMIT 1", (m_id,))
                pay_status = cursor.fetchone()
                conn.close()
                
                current_status = pay_status[0] if pay_status else "لم يُسدد"

                def open_payment_dialog(e, mid=m_id, mname=m_name, cur_st=current_status):
                    status_dropdown = ft.Dropdown(
                        label="حالة السداد",
                        options=[ft.dropdown.Option("تم السداد"), ft.dropdown.Option("لم يُسدد")],
                        value=cur_st
                    )
                    def save_new_status(ev):
                        new_st = status_dropdown.value
                        conn_db = sqlite3.connect("gama3at.db")
                        cur_db = conn_db.cursor()
                        cur_db.execute("DELETE FROM payments WHERE member_id = ?", (mid,))
                        cur_db.execute("INSERT INTO payments (member_id, month_name, status) VALUES (?, ?, ?)", (mid, "الشهر الحالي", new_st))
                        conn_db.commit()
                        conn_db.close()
                        pay_dlg.open = False
                        page.update()
                        gama3a_details_view(gama3a_id, gama3a_name)

                    def close_pay_dlg(ev):
                        pay_dlg.open = False
                        page.update()

                    pay_dlg = ft.AlertDialog(
                        title=ft.Text(f"تحديث حالة السداد: {mname}"),
                        content=status_dropdown,
                        actions=[
                            ft.TextButton("إلغاء", on_click=close_pay_dlg),
                            ft.ElevatedButton("حفظ", bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=save_new_status)
                        ]
                    )
                    page.overlay.append(pay_dlg)
                    pay_dlg.open = True
                    page.update()

                btn_color = ft.Colors.GREEN if current_status == "تم السداد" else ft.Colors.RED
                pay_action_btn = ft.ElevatedButton(
                    content=ft.Text(f"حالة القسط: {current_status}", color=ft.Colors.WHITE, size=12),
                    bgcolor=btn_color,
                    on_click=open_payment_dialog
                )

                is_turn_now = (index == 0)
                card_bg = ft.Colors.AMBER_50 if is_turn_now else ft.Colors.WHITE
                title_text = f"⭐ {m_name} (أسهم: {shares}) [عليه دور القبض]" if is_turn_now else f"{m_name} (أسهم: {shares})"

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.PERSON, color=ft.Colors.AMBER_900 if is_turn_now else ft.Colors.BLUE),
                                title=ft.Text(title_text, weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"أشهر القبض: الشهر ({roles or 'غير محدد'}) \nالأرقام: {p1} {f' - {p2}' if p2 else ''}"),
                                trailing=ft.Row([
                                    ft.IconButton(icon=ft.Icons.EDIT, icon_color=ft.Colors.BLUE, tooltip="تعديل", on_click=lambda e, md=m: open_add_member(e, member_data=md)),
                                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, tooltip="حذف", on_click=lambda e, mid=m_id: delete_member(mid))
                                ], tight=True)
                            ),
                            ft.Row([pay_action_btn] + wa_buttons, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)
                        ]),
                        padding=10,
                        bgcolor=card_bg,
                        border_radius=ft.border_radius.all(8)
                    )
                )
                members_list.controls.append(card)

        add_mem_btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.WHITE), ft.Text("إضافة عضو", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.BLUE,
            on_click=open_add_member
        )

        footer_info = ft.Text("Design and Programming | Eng: Amr El-Sherif | N.O.: 01009191945", size=11, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER)

        page.add(header, pdf_btn, ft.Divider(), members_list, add_mem_btn, ft.Divider(), footer_info)
        page.update()

    home_view()

ft.app(target=main)
