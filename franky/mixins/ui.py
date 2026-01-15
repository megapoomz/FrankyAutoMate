"""
UIMixin - UI helper functions and visual feedback
"""
import customtkinter as ctk
import logging
import time


class UIMixin:
    """Handles UI tab setups, list displays, and visual feedback"""
    
    def log_message(self, message: str, color: str = "white", level: int = logging.INFO):
        """Standardized logging to UI and File"""
        now = time.strftime("%H:%M:%S")
        
        # Log to file
        if level == logging.DEBUG:
            logging.debug(message)
        elif level == logging.WARNING:
            logging.warning(message)
        elif level == logging.ERROR:
            logging.error(message)
        else:
            logging.info(message)
            
        # Log to UI
        try:
            if hasattr(self, 'txt_log') and self.txt_log:
                self.txt_log.configure(state="normal")
                
                # Format color tags
                tag_color = color if color != "white" else ""
                formatted = f"[{now}] {message}\n"
                
                self.txt_log.insert("end", formatted)
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")
        except:
            pass

    def update_list_display(self):
        """Update the action list UI"""
        # Clear existing widgets
        for w in self.action_widgets:
            w.destroy()
        self.action_widgets = []
        
        for widget in self.scroll_actions.winfo_children():
            widget.destroy()
        
        if not self.actions:
            # Empty state message
            empty_frame = ctk.CTkFrame(self.scroll_actions, fg_color="transparent")
            empty_frame.pack(fill="x", pady=20)
            ctk.CTkLabel(
                empty_frame,
                text="📋 ยังไม่มีคำสั่ง\nกดเมนูด้านขวาเพื่อเพิ่มคำสั่ง",
                font=("Segoe UI", 12),
                text_color="#7f8c8d",
                justify="center"
            ).pack(pady=20)
            return
        
        # Display each action
        for i, action in enumerate(self.actions):
            desc = self.get_action_description(action)
            frame = ctk.CTkFrame(
                self.scroll_actions,
                fg_color="#2a2a2a",
                corner_radius=8,
                border_width=1,
                border_color="#444"
            )
            frame.pack(fill="x", padx=5, pady=3)
            frame.bind("<Button-1>", lambda e, idx=i: self.select_action(idx))
            
            lbl = ctk.CTkLabel(
                frame,
                text=f"{i+1}. {desc}",
                font=("Segoe UI", 11),
                anchor="w"
            )
            lbl.pack(side="left", padx=10, pady=8, fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, idx=i: self.select_action(idx))
            
            self.action_widgets.append(frame)

    def highlight_action(self, index):
        """Highlight the currently executing action"""
        for i, widget in enumerate(self.action_widgets):
            if i == index:
                widget.configure(fg_color="#27ae60", border_color="#2ecc71")
            else:
                widget.configure(fg_color="#2a2a2a", border_color="#444")

    def select_action(self, index):
        """Select an action for editing/moving"""
        self.selected_action_index = index
        for i, widget in enumerate(self.action_widgets):
            if i == index:
                widget.configure(border_color="#3498db", border_width=2)
            else:
                widget.configure(border_color="#444", border_width=1)

    def show_click_marker(self, x, y):
        """Show a temporary visual marker at click location"""
        if not self.show_marker:
            return
        
        marker = ctk.CTkToplevel(self)
        marker.overrideredirect(True)
        marker.attributes("-topmost", True)
        marker.attributes("-transparentcolor", "black")
        marker.geometry(f"30x30+{int(x)-15}+{int(y)-15}")
        
        canvas = ctk.CTkCanvas(marker, width=30, height=30, bg="black", highlightthickness=0)
        canvas.pack()
        canvas.create_oval(2, 2, 28, 28, outline="red", width=3)
        
        marker.after(300, marker.destroy)

    def show_found_marker(self, x, y, w=50, h=50):
        """Show a marker for found image/color"""
        if not self.show_marker:
            return
        
        marker = ctk.CTkToplevel(self)
        marker.overrideredirect(True)
        marker.attributes("-topmost", True)
        marker.attributes("-transparentcolor", "black")
        marker.geometry(f"{w}x{h}+{int(x)-w//2}+{int(y)-h//2}")
        
        canvas = ctk.CTkCanvas(marker, width=w, height=h, bg="black", highlightthickness=0)
        canvas.pack()
        canvas.create_rectangle(2, 2, w-2, h-2, outline="green", width=3)
        
        marker.after(500, marker.destroy)
