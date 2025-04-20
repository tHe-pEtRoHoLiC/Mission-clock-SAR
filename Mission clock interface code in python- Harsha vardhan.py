import tkinter as tk
import math
from datetime import datetime, timedelta
from suntime import Sun, SunTimeException
import csv

class MissionClock:
    def __init__(self, root, latitude, longitude, mission_duration):
        # Initialize mission clock
        self.root = root
        self.root.title("Mission Clock for SAR")
        self.root.geometry("800x800")
        self.latitude = latitude
        self.longitude = longitude
        self.calculate_sun_times()
        self.mission_duration = mission_duration
        self.elapsed_minutes = 0
        self.clock_started = False
        self.waypoints = []

        # Define the current location and ground speed attributes
        self.current_location = (latitude, longitude)  # Initial location of the mission
        self.ground_speed = 10  # Assuming ground speed of 10 m/s (can be adjusted as needed)

        # Canvas for drawing the clock
        self.canvas = tk.Canvas(self.root, width=600, height=600, bg='black')
        self.canvas.pack(side=tk.TOP, pady=10)

        # Create override frame and controls
        self.create_override_controls()

        # Start button for clock and mission
        self.start_clock_button = tk.Button(self.root, text="Start Mission", command=self.start_clock_and_mission)
        self.start_clock_button.pack(side=tk.TOP, pady=5)

        # Draw static elements of the clock
        self.define_clock_parameters()
        self.draw_static_clock_elements()

        # Bind mouse click event to add waypoints
        self.canvas.bind("<Button-1>", self.add_waypoint)

        # Add label for current time
        self.time_label = self.canvas.create_text(self.center_x, self.center_y, text="", fill="white", font=("Helvetica", 15, "bold"), tags="time_label")

        # Red pointers for hour and minute rings
        self.hour_pointer = None
        self.minute_pointer = None

        # Draw mission duration arc (40-minute marker)
        self.highlight_mission_duration(0, self.mission_duration.seconds // 60)

        # Highlight sunrise and sunset if they fall within the mission duration
        self.highlight_sun_times()

    def create_override_controls(self):
        # Override frame
        self.override_frame = tk.Frame(self.root)
        self.override_frame.pack(side=tk.LEFT, padx=20, anchor='s')

        # Override title label
        self.override_title_label = tk.Label(self.override_frame, text="Override", font=("Helvetica", 14, "bold"))
        self.override_title_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Override current time input
        self.time_override_label = tk.Label(self.override_frame, text="Override Current Time (HH:MM):")
        self.time_override_label.grid(row=1, column=0, sticky='w')
        self.time_override_entry = tk.Entry(self.override_frame)
        self.time_override_entry.grid(row=1, column=1)
        self.time_override_button = tk.Button(self.override_frame, text="Override Time", command=self.override_current_time)
        self.time_override_button.grid(row=2, column=0, columnspan=2, pady=5)

        # Override elapsed time input
        self.elapsed_override_label = tk.Label(self.override_frame, text="Override Elapsed Time (Minutes):")
        self.elapsed_override_label.grid(row=3, column=0, sticky='w')
        self.elapsed_override_entry = tk.Entry(self.override_frame)
        self.elapsed_override_entry.grid(row=3, column=1)
        self.elapsed_override_button = tk.Button(self.override_frame, text="Override Elapsed Time", command=self.override_elapsed_time)
        self.elapsed_override_button.grid(row=4, column=0, columnspan=2, pady=5)

    def define_clock_parameters(self):
        # Define clock parameters
        self.center_x = 300
        self.center_y = 300
        self.radius_outer = 200
        self.radius_inner = 150
        self.radius_waypoints = 250
        self.radius_minute_ring = 180
        self.radius_hour_ring = 230
        self.radius_battery_ring = 130
        self.radius_battery_boundary = 140

    def draw_static_clock_elements(self):
        # Draw outer and inner rings for the clock
        self.canvas.create_oval(
            self.center_x - self.radius_outer + 9, self.center_y - self.radius_outer + 9,
            self.center_x + self.radius_outer - 9, self.center_y + self.radius_outer - 9,
            outline="white", width=1
        )
        self.canvas.create_oval(
            self.center_x - self.radius_inner, self.center_y - self.radius_inner,
            self.center_x + self.radius_inner, self.center_y + self.radius_inner,
            outline="white", width=1
        )

        # Draw the elapsed time arc behind other elements initially
        self.elapsed_arc = self.canvas.create_arc(
            self.center_x - self.radius_outer + 20, self.center_y - self.radius_outer + 20,
            self.center_x + self.radius_outer - 20, self.center_y + self.radius_outer - 20,
            start=90, extent=0,
            outline="green", width=20, style=tk.ARC, tags="elapsed_arc"
        )

        # Draw the battery level boundary ring
        self.canvas.create_oval(
            self.center_x - self.radius_battery_boundary + 10, self.center_y - self.radius_battery_boundary + 10,
            self.center_x + self.radius_battery_boundary - 10, self.center_y + self.radius_battery_boundary - 10,
            outline="white", width=2
        )

        # Draw the battery level indicator arc initially as blue and at 100%
        self.battery_arc = self.canvas.create_arc(
            self.center_x - self.radius_battery_ring - 10, self.center_y - self.radius_battery_ring - 10,
            self.center_x + self.radius_battery_ring + 10, self.center_y + self.radius_battery_ring + 10,
            start=90, extent=-360, outline="blue", width=15, style=tk.ARC, tags="battery_arc"
        )

        # Draw battery level markers (100%, 50%)
        for angle, label in [(90, "100%"), (-90, "50%")]:
            radian_angle = math.radians(angle)
            x = self.center_x + (self.radius_battery_ring + 10) * math.cos(radian_angle)
            y = self.center_y - (self.radius_battery_ring + 10) * math.sin(radian_angle)
            self.canvas.create_text(x, y, text=label, fill="white", font=("Helvetica", 10, "bold"))

        # Draw battery dash markers
        for i in range(0, 360, 36):
            angle = math.radians(i - 90)
            x_start = self.center_x + (self.radius_battery_ring + 15) * math.cos(angle)
            y_start = self.center_y + (self.radius_battery_ring + 15) * math.sin(angle)
            x_end = self.center_x + self.radius_battery_ring * math.cos(angle)
            y_end = self.center_y + self.radius_battery_ring * math.sin(angle)
            self.canvas.create_line(x_start, y_start, x_end, y_end, fill="white", width=1)

        # Update sunrise and sunset
        self.canvas.create_text(self.center_x, self.center_y - self.radius_inner + 50, text=f"Sunrise: {self.sunrise.strftime('%H:%M')}", fill="yellow", font=("Helvetica", 12, "bold"))
        self.canvas.create_text(self.center_x, self.center_y + self.radius_inner - 50, text=f"Sunset: {self.sunset.strftime('%H:%M')}", fill="orange", font=("Helvetica", 12, "bold"))

        # Draw waypoint ring
        self.canvas.create_oval(
            self.center_x - self.radius_waypoints, self.center_y - self.radius_waypoints,
            self.center_x + self.radius_waypoints, self.center_y + self.radius_waypoints,
            outline="white", width=2, dash=(4, 2)
        )

        # Draw minute markers
        for i in range(0, 60, 5):
            angle = math.radians((i - 135) * 6)
            x = self.center_x + self.radius_minute_ring * math.cos(angle)
            y = self.center_y + self.radius_minute_ring * math.sin(angle)
            self.canvas.create_text(x, y, text=str(i), fill="white", font=("Helvetica", 12, "bold"), tags=f"minute_marker_{i}")

        # Draw minute line markers between 5-minute intervals
        for i in range(0, 60):
            if i % 5 != 0:
                angle = math.radians((i - 135) * 6)
                x_start = self.center_x + (self.radius_minute_ring - 5) * math.cos(angle)
                y_start = self.center_y + (self.radius_minute_ring - 5) * math.sin(angle)
                x_end = self.center_x + self.radius_minute_ring * math.cos(angle)
                y_end = self.center_y + self.radius_minute_ring * math.sin(angle)
                self.canvas.create_line(x_start, y_start, x_end, y_end, fill="white", width=1, tags=f"minute_marker_{i}")

        # Draw hour markers (1, 2, ..., 12)
        for i in range(1, 13):
            angle = math.radians((i * 30) + 270)
            x = self.center_x + (self.radius_minute_ring + (self.radius_hour_ring - self.radius_minute_ring) / 2) * math.cos(angle)
            y = self.center_y + (self.radius_minute_ring + (self.radius_hour_ring - self.radius_minute_ring) / 2) * math.sin(angle)
            self.canvas.create_text(x, y, text=str(i), fill="white", font=("Helvetica", 12, "bold"))

        # Draw hour ring boundary
        self.canvas.create_oval(
            self.center_x - self.radius_hour_ring + 12, self.center_y - self.radius_hour_ring + 12,
            self.center_x + self.radius_hour_ring - 12, self.center_y + self.radius_hour_ring - 12,
            outline="white", width=2
        )

    def calculate_sun_times(self):
        sun = Sun(self.latitude, self.longitude)
        today = datetime.now().date()
        try:
            self.sunrise = sun.get_local_sunrise_time(today).time()
            self.sunset = sun.get_local_sunset_time(today).time()
        except SunTimeException as e:
            print(f"Error: {e}")
            self.sunrise = datetime.now().replace(hour=6, minute=0, second=0).time()  # Default to 6:00 AM
            self.sunset = datetime.now().replace(hour=18, minute=0, second=0).time()  # Default to 6:00 PM

    def highlight_sun_times(self):
        sunrise_minutes = self.sunrise.hour * 60 + self.sunrise.minute
        sunset_minutes = self.sunset.hour * 60 + self.sunset.minute
        mission_end_minutes = self.mission_duration.seconds // 60

        for sun_time, color in [(sunrise_minutes, "yellow"), (sunset_minutes, "orange")]:
            if sun_time <= mission_end_minutes:
                minute_marker = sun_time % 60
                angle = math.radians((minute_marker - 135) * 6)
                x = self.center_x + (self.radius_minute_ring + 15) * math.cos(angle)
                y = self.center_y + (self.radius_minute_ring + 15) * math.sin(angle)
                self.canvas.create_oval(
                    x - 10, y - 10, x + 10, y + 10,
                    outline=color, width=3, tags=f"sun_time_{sun_time}"
                )

    def draw_elapsed_time(self):
        end_angle = -(self.elapsed_minutes / 60.0) * 360 + 270
        self.canvas.itemconfig(self.elapsed_arc, extent=end_angle - 270)

        if self.elapsed_minutes == 20:
            self.blink_arc(self.elapsed_arc, "orange")
        elif self.elapsed_minutes == 30:
            self.blink_arc(self.elapsed_arc, "red")

        battery_extent = 360 * (1 - (self.elapsed_minutes / 40))
        self.canvas.itemconfig(self.battery_arc, extent=-battery_extent)

    def blink_arc(self, arc_id, color, blink_count=6, interval=500):
        if blink_count > 0:
            current_color = self.canvas.itemcget(arc_id, "outline")
            new_color = "black" if current_color == color else color
            self.canvas.itemconfig(arc_id, outline=new_color)
            self.root.after(interval, self.blink_arc, arc_id, color, blink_count - 1, interval)
        else:
            self.canvas.itemconfig(arc_id, outline=color)

    def update_pointer(self):
        # Update hour pointer
        if self.hour_pointer:
            self.canvas.delete(self.hour_pointer)

        current_time = datetime.now() if not hasattr(self, 'overridden_time') else self.overridden_time
        hour = current_time.hour % 12 + current_time.minute / 60.0
        hour_angle = math.radians((hour / 12.0) * 360 - 90)
        x_start = self.center_x + (self.radius_minute_ring + 13) * math.cos(hour_angle)
        y_start = self.center_y + (self.radius_minute_ring + 13) * math.sin(hour_angle)
        x_end = self.center_x + (self.radius_hour_ring - 12) * math.cos(hour_angle)
        y_end = self.center_y + (self.radius_hour_ring - 12) * math.sin(hour_angle)
        self.hour_pointer = self.canvas.create_line(x_start, y_start, x_end, y_end, fill="red", width=5)

        # Update minute pointer
        if self.minute_pointer:
            self.canvas.delete(self.minute_pointer)

        minute = current_time.minute + current_time.second / 60.0
        minute_angle = math.radians((minute / 60.0) * 360 - 90)
        x_start_min = self.center_x + (self.radius_inner + 10) * math.cos(minute_angle)
        y_start_min = self.center_y + (self.radius_inner + 10) * math.sin(minute_angle)
        x_end_min = self.center_x + self.radius_minute_ring * math.cos(minute_angle)
        y_end_min = self.center_y + self.radius_minute_ring * math.sin(minute_angle)
        self.minute_pointer = self.canvas.create_line(x_start_min, y_start_min, x_end_min, y_end_min, fill="red", width=3)

    def add_waypoint(self, event):
        dx = event.x - self.center_x
        dy = event.y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)

        if abs(distance - self.radius_waypoints) < 15:
            angle = math.degrees(math.atan2(dy, dx))
            radians = math.radians(angle)
            x = self.center_x + self.radius_waypoints * 0.95 * math.cos(radians)
            y = self.center_y + self.radius_waypoints * 0.95 * math.sin(radians)

            size = 10
            points = [
                (x, y - size / 2),
                (x - size / 2, y + size / 2),
                (x + size / 2, y + size / 2)
            ]
            self.canvas.create_polygon(points, fill="yellow", outline="black", tags="waypoint")

    def start_clock_and_mission(self):
        if not self.clock_started:
            self.clock_started = True
            self.elapsed_minutes = 0
            self.update_clock()
            self.update_digital_clock()

    def override_current_time(self):
        time_str = self.time_override_entry.get()
        try:
            override_time = datetime.strptime(time_str, "%H:%M")
            self.overridden_time = datetime.now().replace(hour=override_time.hour, minute=override_time.minute, second=0, microsecond=0)
            self.update_pointer()
        except ValueError:
            print("Invalid time format. Please use HH:MM.")

    def override_elapsed_time(self):
        try:
            new_elapsed_minutes = int(self.elapsed_override_entry.get())
            if 0 <= new_elapsed_minutes <= 60:
                self.elapsed_minutes = new_elapsed_minutes
                self.draw_elapsed_time()
            else:
                print("Elapsed time should be between 0 and 60 minutes.")
        except ValueError:
            print("Invalid elapsed time. Please enter an integer.")

    def update_clock(self):
        if self.clock_started and self.elapsed_minutes < 60:
            self.draw_elapsed_time()
            self.update_pointer()
            self.elapsed_minutes += 1
            self.root.after(60000, self.update_clock)

    def highlight_mission_duration(self, start_minute, duration_minutes):
        start_angle = 90 - (start_minute * 6)
        extent = -(duration_minutes * 6)
        self.canvas.create_arc(
            self.center_x - (self.radius_minute_ring - 23), self.center_y - (self.radius_minute_ring - 23),
            self.center_x + (self.radius_minute_ring - 23), self.center_y + (self.radius_minute_ring - 23),
            start=start_angle, extent=extent,
            outline="red", width=15, style=tk.ARC, tags="mission_arc"
        )

    def update_digital_clock(self):
        current_time = datetime.now() if not hasattr(self, 'overridden_time') else self.overridden_time
        self.canvas.itemconfig(self.time_label, text=current_time.strftime("%H:%M:%S"))
        self.update_pointer()
        if not hasattr(self, 'overridden_time'):
            self.root.after(1000, self.update_digital_clock)

if __name__ == "__main__":
    root = tk.Tk()
    latitude = 51.5074  # Latitude for London
    longitude = -0.1278  # Longitude for London
    mission_duration = timedelta(minutes=40)
    app = MissionClock(root, latitude, longitude, mission_duration)
    root.mainloop()