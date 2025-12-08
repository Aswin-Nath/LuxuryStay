import { Component, OnInit, AfterViewInit, ViewChild, ElementRef, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AdminNavbarComponent } from '../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../layout/Admin/admin-sidebar/admin-sidebar.component';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

interface Booking {
  id: string;
  guest: string;
  roomNo: number;
  roomType: string;
  bookingDate: string;
  checkIn: string;
  checkOut: string;
  nights: number;
  pricePerNight: number;
  totalAmount: number;
  refunded: number;
  cancellationReason: string | null;
  status: string;
  reviewRating: number | null;
  reviewText: string | null;
  lifetimeSpend: number;
}

interface Room {
  id: number;
  type: string;
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css']
})
export class AdminDashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('dailyBookingsChart') dailyChartRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('roomTypeChart') roomTypeChartRef!: ElementRef<HTMLCanvasElement>;

  private dailyChart: Chart | null = null;
  private roomTypeChart: Chart | null = null;

  // Filter state
  currentRange = '1W';
  filterFrom: string | null = null;
  filterTo: string | null = null;
  showCustomDates = false;
  statusFilter = 'all';
  fromDate = '';
  toDate = '';

  // KPIs
  totalBookings = 0;
  netRevenue = 0;
  refundsSent = 0;
  roomsAvailable = 0;
  cancelRate = 0;
  noShowRate = 0;
  retentionRate = 0;
  adr = 0;
  revpar = 0;
  refundPercent = 0;

  // Tables
  checkoutsList: Booking[] = [];
  checkinsList: Booking[] = [];
  refundsList: Booking[] = [];
  topGuestsList: Booking[] = [];

  // Data
  private ROOMS: Room[] = [
    { id: 101, type: 'Single' },
    { id: 102, type: 'Single' },
    { id: 201, type: 'Double' },
    { id: 202, type: 'Double Deluxe' },
    { id: 301, type: 'Suite' },
    { id: 302, type: 'Suite' },
    { id: 401, type: 'Family' },
    { id: 402, type: 'Family' },
    { id: 501, type: 'Executive' }
  ];

  private BOOKINGS: Booking[] = [];

  // Toast
  showToast = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' = 'success';

  constructor() {}

  ngOnInit(): void {
    this.BOOKINGS = this.generateBookings(320);
    this.applyFiltersAndRender('1W');
  }

  ngAfterViewInit(): void {
    this.initCharts();
  }

  ngOnDestroy(): void {
    if (this.dailyChart) this.dailyChart.destroy();
    if (this.roomTypeChart) this.roomTypeChart.destroy();
  }

  // ========== DATA GENERATION ==========
  private generateBookings(n: number): Booking[] {
    const bookings: Booking[] = [];
    const names = ['Asha', 'Ravi', 'Maya', 'Karan', 'Sima', 'Vikram', 'Neha', 'Rohit', 'Lata', 'Imran', 'Priya', 'Arjun', 'Sunita'];
    const reasons = ['Change of plan', 'Room issue', 'Weather', 'Illness', 'Double booking', 'Price issue'];
    const today = new Date();

    for (let i = 0; i < n; i++) {
      const bookDate = this.addDays(today, this.rand(-45, 45));
      const lead = this.rand(0, 30);
      const checkIn = this.addDays(bookDate, lead);
      const stayLen = this.rand(1, 7);
      const checkOut = this.addDays(checkIn, stayLen);
      const room = this.ROOMS[this.rand(0, this.ROOMS.length - 1)];
      const statusRoll = Math.random();
      
      let status = 'confirmed';
      if (statusRoll < 0.06) status = 'cancelled';
      else if (statusRoll < 0.10) status = 'no-show';
      else if (new Date(checkIn) <= new Date() && new Date(checkOut) >= new Date() && status === 'confirmed') status = 'checkedin';
      else if (new Date(checkOut) < new Date() && status === 'confirmed') status = 'checkedout';

      const pricePerNight = room.type.toLowerCase().includes('suite') ? 9000 :
        room.type.toLowerCase().includes('executive') ? 7000 :
        room.type.toLowerCase().includes('family') ? 6500 :
        room.type.toLowerCase().includes('double') ? 4500 : 2500;

      const nights = stayLen;
      const totalAmount = pricePerNight * nights;
      const refunded = status === 'cancelled' ? Math.round(totalAmount * Math.random() * 0.9) : 0;
      const reviewRating = (status === 'checkedout' && Math.random() > 0.3) ? this.rand(3, 5) : null;
      const reviewText = reviewRating ? ['Great stay', 'Will come again', 'Good service', 'Average experience', 'Loved it'][this.rand(0, 4)] : null;

      bookings.push({
        id: 'BKG' + (10000 + i),
        guest: names[this.rand(0, names.length - 1)] + ' ' + String.fromCharCode(65 + this.rand(0, 20)) + '.',
        roomNo: room.id,
        roomType: room.type,
        bookingDate: this.formatDateISO(bookDate),
        checkIn: this.formatDateISO(checkIn),
        checkOut: this.formatDateISO(checkOut),
        nights,
        pricePerNight,
        totalAmount,
        refunded,
        cancellationReason: status === 'cancelled' ? reasons[this.rand(0, reasons.length - 1)] : null,
        status,
        reviewRating,
        reviewText,
        lifetimeSpend: this.rand(5000, 250000)
      });
    }

    return bookings.sort((a, b) => new Date(a.checkIn).getTime() - new Date(b.checkIn).getTime());
  }

  // ========== UTILITY FUNCTIONS ==========
  private rand(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  private addDays(date: Date, days: number): Date {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
  }

  private formatDateISO(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  formatCurrency(num: number): string {
    return '₹' + num.toLocaleString();
  }

  // ========== FILTERS ==========
  selectRange(range: string): void {
    this.currentRange = range;
    this.showCustomDates = range === 'custom';
    if (range !== 'custom') {
      this.applyFiltersAndRender(range);
    }
  }

  applyCustomRange(): void {
    if (this.fromDate && this.toDate) {
      this.applyFiltersAndRender('custom', this.fromDate, this.toDate);
    }
  }

  onStatusFilterChange(): void {
    this.applyFiltersAndRender(this.currentRange, this.filterFrom || undefined, this.filterTo || undefined);
  }

  applyFiltersAndRender(range: string, from?: string, to?: string): void {
    const today = new Date();
    let start: Date, end: Date;

    if (range === '1D') {
      start = new Date(today);
      end = new Date(today);
    } else if (range === '1W') {
      start = this.addDays(today, -7);
      end = this.addDays(today, 7);
    } else if (range === '1M') {
      start = this.addDays(today, -30);
      end = this.addDays(today, 30);
    } else if (range === '1Y') {
      start = this.addDays(today, -365);
      end = this.addDays(today, 365);
    } else if (range === 'custom' && from && to) {
      start = new Date(from);
      end = new Date(to);
    } else {
      start = this.addDays(today, -7);
      end = this.addDays(today, 7);
    }

    this.filterFrom = this.formatDateISO(start);
    this.filterTo = this.formatDateISO(end);

    let filtered = this.BOOKINGS.filter(b => {
      const ch = new Date(b.checkIn);
      return ch >= start && ch <= end;
    });

    // Apply status filter
    if (this.statusFilter !== 'all') {
      filtered = filtered.filter(b => b.status === this.statusFilter);
    }

    // Calculate KPIs
    this.totalBookings = filtered.length;
    this.netRevenue = filtered.reduce((s, b) => s + (b.totalAmount - (b.refunded || 0)), 0);
    this.refundsSent = filtered.reduce((s, b) => s + (b.refunded || 0), 0);
    this.roomsAvailable = this.ROOMS.length;

    const cancCount = filtered.filter(x => x.status === 'cancelled').length;
    this.cancelRate = filtered.length ? Math.round((cancCount / filtered.length) * 10000) / 100 : 0;

    const noShowCount = filtered.filter(x => x.status === 'no-show').length;
    this.noShowRate = filtered.length ? Math.round((noShowCount / filtered.length) * 10000) / 100 : 0;

    const returning = filtered.filter(x => x.lifetimeSpend > 50000).length;
    this.retentionRate = filtered.length ? Math.round((returning / filtered.length) * 10000) / 100 : 0;

    const roomsSold = filtered.filter(x => x.status !== 'cancelled').reduce((s, b) => s + b.nights, 0);
    const revenue = filtered.reduce((s, b) => s + (b.totalAmount - (b.refunded || 0)), 0);
    this.adr = roomsSold ? Math.round(revenue / roomsSold) : 0;

    const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
    this.revpar = Math.round(revenue / (this.ROOMS.length * days));

    this.refundPercent = this.netRevenue ? Math.round((this.refundsSent / this.netRevenue) * 10000) / 100 : 0;

    // Update tables
    this.renderCheckouts(filtered);
    this.renderCheckins(filtered);
    this.renderRefunds(filtered);
    this.renderTopGuests(filtered);

    // Update charts
    this.updateDailyChart(filtered, start, end);
    this.updateRoomTypeChart(filtered);
  }

  // ========== TABLES ==========
  private renderCheckouts(list: Booking[]): void {
    const now = new Date();
    this.checkoutsList = list
      .filter(b => new Date(b.checkOut) >= now && b.status !== 'cancelled')
      .sort((a, b) => new Date(a.checkOut).getTime() - new Date(b.checkOut).getTime())
      .slice(0, 10);
  }

  private renderCheckins(list: Booking[]): void {
    const now = new Date();
    this.checkinsList = list
      .filter(b => new Date(b.checkIn) >= now && b.status !== 'cancelled')
      .sort((a, b) => new Date(a.checkIn).getTime() - new Date(b.checkIn).getTime())
      .slice(0, 10);
  }

  private renderRefunds(list: Booking[]): void {
    this.refundsList = list
      .filter(b => (b.refunded || 0) > 0)
      .sort((a, b) => new Date(b.checkIn).getTime() - new Date(a.checkIn).getTime());
  }

  private renderTopGuests(list: Booking[]): void {
    this.topGuestsList = [...list]
      .sort((a, b) => b.lifetimeSpend - a.lifetimeSpend)
      .slice(0, 8);
  }

  // ========== CHARTS ==========
  private initCharts(): void {
    if (this.dailyChartRef?.nativeElement) {
      const ctx = this.dailyChartRef.nativeElement.getContext('2d');
      if (ctx) {
        const height = this.dailyChartRef.nativeElement.clientHeight || 320;
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, 'rgba(250,204,21,0.45)');
        gradient.addColorStop(1, 'rgba(250,204,21,0.06)');

        this.dailyChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: [],
            datasets: [
              {
                label: 'Confirmed Bookings',
                data: [],
                borderColor: '#f59e0b',
                borderWidth: 3,
                backgroundColor: gradient,
                tension: 0.38,
                fill: true,
                pointRadius: 5,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#f59e0b',
                pointHoverRadius: 7
              },
              {
                label: 'Cancelled Bookings',
                data: [],
                borderColor: '#ef4444',
                borderWidth: 2,
                backgroundColor: 'rgba(239,68,68,0.1)',
                tension: 0.38,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#ef4444',
                pointHoverRadius: 6,
                borderDash: [6, 4]
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
              legend: { display: true },
              tooltip: {
                backgroundColor: '#111827',
                titleColor: '#facc15',
                bodyColor: '#fff',
                padding: 10,
                cornerRadius: 8
              }
            },
            scales: {
              x: { grid: { display: false }, ticks: { color: '#6b7280' } },
              y: {
                beginAtZero: true,
                grid: { color: 'rgba(0,0,0,0.05)' },
                ticks: { color: '#6b7280' }
              }
            }
          }
        });
      }
    }

    if (this.roomTypeChartRef?.nativeElement) {
      const ctx = this.roomTypeChartRef.nativeElement.getContext('2d');
      if (ctx) {
        this.roomTypeChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: [],
            datasets: [{
              data: [],
              backgroundColor: [
                '#f59e0b', '#ef4444', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899'
              ],
              borderWidth: 2,
              borderColor: '#fff'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom' }
            }
          }
        });
      }
    }
  }

  private updateDailyChart(list: Booking[], start: Date, end: Date): void {
    if (!this.dailyChart) return;

    const labels: string[] = [];
    const confirmedData: number[] = [];
    const cancelledData: number[] = [];

    const days = Math.min(14, Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
    
    for (let i = 0; i < days; i++) {
      const d = this.addDays(start, i);
      const dateStr = this.formatDateISO(d);
      labels.push(dateStr);
      
      const dayBookings = list.filter(b => b.checkIn === dateStr);
      confirmedData.push(dayBookings.filter(b => b.status !== 'cancelled').length);
      cancelledData.push(dayBookings.filter(b => b.status === 'cancelled').length);
    }

    this.dailyChart.data.labels = labels;
    this.dailyChart.data.datasets[0].data = confirmedData;
    this.dailyChart.data.datasets[1].data = cancelledData;
    this.dailyChart.update();
  }

  private updateRoomTypeChart(list: Booking[]): void {
    if (!this.roomTypeChart) return;

    const revenueByType: { [key: string]: number } = {};
    list.forEach(b => {
      if (b.status !== 'cancelled') {
        revenueByType[b.roomType] = (revenueByType[b.roomType] || 0) + b.totalAmount - (b.refunded || 0);
      }
    });

    this.roomTypeChart.data.labels = Object.keys(revenueByType);
    this.roomTypeChart.data.datasets[0].data = Object.values(revenueByType);
    this.roomTypeChart.update();
  }

  // ========== ACTIONS ==========
  exportCsv(): void {
    this.displayToast('CSV Export started...', 'info');
    // TODO: Implement CSV export
  }

  backupData(): void {
    this.displayToast('Backup initiated...', 'success');
    // TODO: Implement backup
  }

  displayToast(message: string, type: 'success' | 'error' | 'info'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.showToast = true;

    setTimeout(() => {
      this.showToast = false;
    }, 3000);
  }

  getToastIcon(): string {
    switch (this.toastType) {
      case 'success': return 'check_circle';
      case 'error': return 'error';
      case 'info': return 'info';
      default: return 'check_circle';
    }
  }

  getToastClass(): string {
    switch (this.toastType) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'info': return 'bg-blue-500';
      default: return 'bg-green-500';
    }
  }
}
