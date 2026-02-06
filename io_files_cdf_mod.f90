module io_files_cdf_mod

  use netcdf
  use read_args_mod

! Open/closes reads/writes NetCDF files

  ! Public fields
  ! --------------
  ! Size of domain
  integer                   :: ni,nj

  ! RPN files   : Current validity date
  ! NetCDF files: Time step counter
  integer                   :: datev

  ! Private fields
  ! --------------
  ! Unit numbers - set in main program
  integer, private :: iun_p, iun_v, iun_w, oun, dun
  integer, private :: id_p, id_ps, id_v, id_w
  integer, private :: ier, l_ni,l_nj, nt

  ! Date/time
  integer, dimension(:), allocatable :: dates, times

  ! 3-D data fields
!  real, dimension(:,:,:), allocatable :: cfield_3d
  real, dimension(:,:,:), allocatable :: pfield_3d
  real, dimension(:,:,:), allocatable :: psfield_3d
  real, dimension(:,:,:), allocatable :: vfield_3d
  real, dimension(:,:,:), allocatable :: wfield_3d

contains

! ============================================================================

! Subroutines to read general input files

! Routine to open input file
! --------------------------
subroutine input_file_open (ifile, plot_10mWind_L)
  implicit none
  character(len=1024), intent(in) :: ifile
  logical            , intent(in) :: plot_10mWind_L

  ! Local variables 
  character(len=1024) :: vfile, wfile
  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in

  integer :: d,dsize
  character(len=64) :: dname, vname

  ! Open the pressure input file
  iun_p = 10
print *,'Open input file'
  ier = nf90_open(ifile, nf90_nowrite, iun_p)

  if ( ier /= 0 ) then
    print *,''
    print *,' Something went wrong opening the file:'
    print *,'   ',trim(ifile)
    print *,'     ---------  ABORT  ----------'
    print *,''
    stop
  end if

  ! Check content of input file
  ! ---------------------------
  ier = nf90_inquire(iun_p, ndims_in, nvars_in, ngatts_in, unlimdimid_in)
print*,ndims_in, nvars_in, ngatts_in, unlimdimid_in

  ! Determine grid size
  ni = 0
  nj = 0
  do d=1,ndims_in
    ier = nf90_inquire_dimension(iun_p,d,dname,dsize)
!print*,d,dname,dsize
    select case (dname)
      case ("lon","rlon","longitude","x") 
!        xname = dname
        ni = dsize
      case ("lat","rlat","latitude","y")
!        yname = dname
        nj = dsize
    end select
  end do

  if ( ni == 0 .or. nj == 0 ) then
    print *,''
    print *,' Error: Grid size could not get determined'
    print *,"        Expected: 'lon/rlon/longitude/x' resp. 'lat/rlat/latitude/y'."
    print *,'        ----- ABORT -----'
    print *,''
    stop
  end if

  ! Initialize time step counter
  datev = 0

  print*,'ni,nj:',ni,nj


  ! Open other input files
  ! Vorticity file
  iun_v = 21
  vfile = ifile(1:len_trim(ifile)-7) // 'vort.nc'
print *,'Vorticity file: ',trim(vfile)
  ier = nf90_open(vfile, nf90_nowrite, iun_v)

  ! Wind file
  if (plot_10mWind_L) then
    iun_w = 22
    wfile = ifile(1:len_trim(ifile)-7) // 'wind.nc'
print *,'Surface wind file: ',trim(wfile)
    ier = nf90_open(wfile, nf90_nowrite, iun_w)
  end if

end subroutine input_file_open


! Routine to close input file
! ---------------------------
subroutine input_file_close (p_field, plot_10mWind_L)
  implicit none

  character(len=4), intent(in) :: p_field
  logical         , intent(in) :: plot_10mWind_L

  ! Deallocate 3-D field
!  deallocate (cfield_3d)
  deallocate (pfield_3d)
  if (p_field == 'PNS ' ) deallocate (psfield_3d)
  deallocate (vfield_3d)
  if (plot_10mWind_L) deallocate (wfield_3d)

  deallocate (dates, times)

  ! Close files
  ier = nf90_close(iun_p)
  ier = nf90_close(iun_v)
  if (plot_10mWind_L) ier = nf90_close(iun_w)

end subroutine input_file_close


! Routine to determine timestep
! -----------------------------
! Read first two pressure fields to determine time step
! and other grid related fields
subroutine input_file_deltat (deltat, p_field)
  implicit none

  character(len=4), intent(in)  :: p_field
  integer,          intent(out) :: deltat

  ! Local variables 
  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in
  integer :: dsize, xtype, ndims, len, attnum
  character(len=64) :: dname, vname
  real*8   , dimension(:), allocatable :: tfield_r8
  real     , dimension(:), allocatable :: tfield_r4
  integer  , dimension(:), allocatable :: tfield_i4
  integer*2, dimension(:), allocatable :: tfield_i2
  integer*8, dimension(:), allocatable :: tfield_i8

  integer :: d,id, s1
  character(len=64) :: unit_S, calendar_S

  integer :: year, month, day, hour, minute, second

  ! Check content of input file
  ier = nf90_inquire(iun_p, ndims_in, nvars_in, ngatts_in, unlimdimid_in)
print*,ndims_in, nvars_in, ngatts_in, unlimdimid_in

  ! Find time ID and size
  id = 0
  do d=1,ndims_in
    ier = nf90_inquire_dimension(iun_p,d,dname,dsize)
!print*,'d,dname,dsize:',d,dname,dsize

    if (dname == "time" .and. dsize >= 2) then
      id = d
      nt = dsize
    end if

  end do

  if (id == 0) then
    print *,''
    print *,' Error: Time variable could not be found.'
    print *,"        Expected: 1-D dimension called 'time' with at least 2 time steps."
    print *,'        ----- ABORT -----'
    print *,''
    stop
  end if


  ! Read time
  ! Get type of time variable
  do d=1,nvars_in
    ier = nf90_inquire_variable(iun_p,d,dname,xtype,ndims)
print*,'d,dname,dsize,xtype:',d,dname(1:15),dsize,xtype

    if (dname == "time") then
      id = d
      exit
    end if
  end do

!  ier = nf90_inquire_variable(iun_p,id,vname,xtype,ndims)
print*,'iun_p,id,xtype,ndims:',iun_p,id,xtype,ndims

  allocate (tfield_r8(nt))

  select case (xtype)
    case (NF90_SHORT)  ; allocate (tfield_i2(nt))
                         ier = nf90_get_var(iun_p, id, tfield_i2)
                         tfield_r8 = dble(tfield_i2)
                         deallocate (tfield_i2)
    case (NF90_INT)    ; allocate (tfield_i4(nt))
                         ier = nf90_get_var(iun_p, id, tfield_i4)
                         tfield_r8 = dble(tfield_i4)
                         deallocate (tfield_i4)
    case (NF90_FLOAT)  ; allocate (tfield_r4(nt))
                         ier = nf90_get_var(iun_p, id, tfield_r4)
                         tfield_r8 = dble(tfield_r4)
                         deallocate (tfield_r4)
    case (NF90_DOUBLE) ; ier = nf90_get_var(iun_p, id, tfield_r8)
    case (NF90_INT64)  ; allocate (tfield_i8(nt))
                         ier = nf90_get_var(iun_p, id, tfield_i8)
                         tfield_r8 = dble(tfield_i8)
                         deallocate (tfield_i8)
    case default
      print *,''
      print *," Error: Type of 'time' dimension variable is: ", xtype
      print *,"        but must be of type 3, 4, 5, 6 or 10:"
      print *,'        NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE,  NF90_INT64:'
      print *,'  ',    NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE,  NF90_INT64
      print *,'        ----- ABORT -----'
      print *,''
      stop
  end select
!print*,'time:',tfield_r8
!stop

  ! Get time unit and calendar
  ier = nf90_get_att(iun_p, id, 'calendar', calendar_S)
  ier = nf90_get_att(iun_p, id, 'units', unit_S)
print *,'unit:',unit_S
  if ( ier /= 0 ) then
    print *,''
    print *," Error: Attribute 'units' of dimension 'time' not found."
    print *,'        ----- ABORT -----'
    print *,''
    stop
  end if


  ! Decipher units
  ! Get start of 'since' in unit string
  s1 = index(unit_S, 'since')
print*,'unit_S:',unit_S
print*,'Start of "since": ', index(unit_S, 'since')
print*,'Ttype: ',trim(unit_S(1:s1-1))

  ! Convert interval to seconds
  select case (trim(unit_S(1:s1-1)))
    case ('seconds') ; deltat = (tfield_r8(2) - tfield_r8(1))
    case ('minutes') ; deltat = (tfield_r8(2) - tfield_r8(1)) *    60.
    case ('hours')   ; deltat = (tfield_r8(2) - tfield_r8(1)) *  3600.
    case ('days')    ; deltat = (tfield_r8(2) - tfield_r8(1)) * 86400.
    case default
      print *,''
      print *," Error: Attribute 'units' of dimension 'time' needs to be in:"
      print *,"        'seconds/minutes/hours/days since YYYY-MM-DD hh:mm:ss'"
      print *,'        ----- ABORT -----'
      print *,''
      stop
  end select
print*,'deltat = ',deltat


  ! Decode dates/times
  ! ==================
!  call decode_time (calendar_S, unit_S, tfield_r8, 33)

print *,'    NF90_BYTE,  NF90_CHAR,  NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE, NF90_INT64:'
print *,NF90_BYTE, NF90_CHAR, NF90_SHORT, NF90_INT, NF90_FLOAT, NF90_DOUBLE, NF90_INT64


  deallocate (tfield_r8)

end subroutine input_file_deltat


! ----------------------------------------------------------------------------

! Routine to decode date/time
! ---------------------------

!subroutine decode_time (calendar_S, unit_S, tfield_r8, nt)
subroutine decode_time (iun)

  implicit none

  integer, intent(in) :: iun

  ! Local variables 
  real*8   , dimension(:), allocatable :: tfield_r8
  real     , dimension(:), allocatable :: tfield_r4
  integer  , dimension(:), allocatable :: tfield_i4
  integer*2, dimension(:), allocatable :: tfield_i2
  integer*8, dimension(:), allocatable :: tfield_i8

  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in
  integer :: dsize, xtype, ndims
  character(len=64) :: dname, vname
  integer :: d,id

  real*8  :: cfac_sec, cfac_day
  character(len=64) :: unit_S, calendar_S

  integer :: s1, t
  integer :: year, month, day, hour, minute, second
  integer :: vyear, vmonth, vday, vhour, vminute, vsecond
  integer :: add_days, add_secs
  integer*8 :: remain_d, remain_s
  integer :: N, N1, N2, N3
  integer :: JD_current, JD_start, I, J, L


  ! Check content of input file
  ier = nf90_inquire(iun, ndims_in, nvars_in, ngatts_in, unlimdimid_in)
!print*,ndims_in, nvars_in, ngatts_in, unlimdimid_in

  ! Find time ID and size
  id = 0
  do d=1,ndims_in
    ier = nf90_inquire_dimension(iun,d,dname,dsize)
!print*,d,dname,dsize

    if (dname == "time" .and. dsize >= 2) then
      id = d
      nt = dsize
    end if

  end do

  ! Get id of time variable
  do d=1,nvars_in
    ier = nf90_inquire_variable(iun_p,d,dname,xtype,ndims)
!print*,'d,dname,dsize:',d,dname,dsize

    if (dname == "time") then
      id = d
      exit
    end if
  end do

  ! Get time unit and calendar
  ier = nf90_get_att(iun, id, 'calendar', calendar_S)
  ier = nf90_get_att(iun, id, 'units', unit_S)
print *,'unit:',unit_S
  if ( ier /= 0 ) then
    print *,''
    print *," Error: Attribute 'units' of dimension 'time' not found."
    print *,'        ----- ABORT -----'
    print *,''
    stop
  end if

  ! Read time
  allocate (tfield_r8(nt))

  select case (xtype)
    case (NF90_SHORT) ; allocate (tfield_i2(nt))
               ier = nf90_get_var(iun_p, id, tfield_i2)
               tfield_r8 = dble(tfield_i2)
               deallocate (tfield_i2)
    case (NF90_INT) ; allocate (tfield_i4(nt))
               ier = nf90_get_var(iun_p, id, tfield_i4)
               tfield_r8 = dble(tfield_i4)
               deallocate (tfield_i4)
    case (NF90_FLOAT) ; allocate (tfield_r4(nt))
               ier = nf90_get_var(iun_p, id, tfield_r4)
               tfield_r8 = dble(tfield_r4)
               deallocate (tfield_r4)
    case (NF90_DOUBLE) ; ier = nf90_get_var(iun_p, id, tfield_r8)
    case (NF90_INT64) ; allocate (tfield_i8(nt))
               ier = nf90_get_var(iun_p, id, tfield_i8)
               tfield_r8 = dble(tfield_i8)
               deallocate (tfield_i8)
  end select
!print*,'time:',tfield_r8

print *,'calendar:', calendar_S
print *,'time    :', unit_S

  ! Make sure calendar is digestible
  if (calendar_S /= 'proleptic_gregorian' .and. &
      calendar_S /= '365_day'             .and. &
      calendar_S /= '360_day'             .and. &
      calendar_S /= 'noleap') then
    print *,''
    print *," Error: 'time:calendar' must be one of the below:"
    print *,"        'proleptic_gregorian', '365_day', '360_day', 'noleap'"
    print *,'        ----- ABORT -----'
    print *,''
    stop
  end if

  ! Get start of 'since' in unit string
  s1 = index(unit_S, 'since')
print*,'Start of "since": ', index(unit_S, 'since')

  ! Make sure time unit is digestible
  if (s1 == 0) then
      print *,''
      print *," Error: Attribute 'units' of dimension 'time' needs to be in:"
      print *,"        'seconds/minutes/hours/days since YYYY-MM-DD hh:mm:ss'"
      print *,'        ----- ABORT -----'
      print *,''
      stop
  end if

  ! Determine conversion factor to convert time to seconds and days
!print*,'Ttype: ',trim(unit_S(1:s1-1))
  select case (trim(unit_S(1:s1-1)))
    case ('seconds') ; cfac_sec =     1. ; cfac_day = 86400.
    case ('minutes') ; cfac_sec =    60. ; cfac_day =  1440.
    case ('hours')   ; cfac_sec =  3600. ; cfac_day =    24.
    case ('days')    ; cfac_sec = 86400. ; cfac_day =     1.
    case default
      print *,''
      print *," Error: Attribute 'units' of dimension 'time' needs to be in:"
      print *,"        'seconds/minutes/hours/days since YYYY-MM-DD hh:mm:ss'"
      print *,'        ----- ABORT -----'
      print *,''
      stop
  end select

  ! Read start date/time
  read (unit_S(s1+ 6:s1+ 9),'(i4)') year
  read (unit_S(s1+11:s1+12),'(i2)') month
  read (unit_S(s1+14:s1+15),'(i2)') day
  read (unit_S(s1+17:s1+18),'(i2)') hour
  read (unit_S(s1+20:s1+21),'(i2)') minute
  read (unit_S(s1+23:s1+24),'(i2)') second
print*,'year:',year,month,day,hour,minute,second

  allocate (dates(nt), times(nt))


  ! Calculate date/time depending on calendar
  ! =========================================
  select case (calendar_S)

    case ('proleptic_gregorian')
    !      =================== 
      print *,'proleptic_gregorian'

      add_secs = hour*3600 + minute*60 + second
      hour   = 0
      minute = 0
      second = 0

      ! Convert start date from a Gregorian calendar date to a Julian date. 
      ! Valid for any Gregorian calendar date producing a Julian date greater than zero.
      ! From: https://aa.usno.navy.mil/faq/JD_formula
      JD_start = day-32075+1461*(year+4800+(month-14)/12)/4+367*(month-2-(month-14)/12*12) / 12-3*((year+4900+(month-14)/12)/100)/4

      do t=1,nt
        remain_d = (tfield_r8(t)*cfac_sec+add_secs)/86400.d0 ! Full days of time passed
        JD_current = JD_start + remain_d

        L = JD_current + 68569
        N = 4*L/146097
        L = L-(146097*N+3)/4
        I = 4000*(L+1)/1461001
        L = L-1461*I/4+31
        J = 80*L/2447
        vday   = L-2447*J/80
        L = J/11
        vmonth = J+2-12*L
        vyear  = 100*(N-49)+I+L

        remain_s = int(dmod(tfield_r8(t)*cfac_sec+add_secs, 86400.d0))
!print*,'tfield_r8(t), remain_s:', tfield_r8(t), remain_s, cfac_sec,add_secs
        vhour    =   hour + remain_s/3600.
        remain_s = remain_s - (vhour-hour)*3600.
        vminute  = minute + remain_s/60.
        remain_s = remain_s - (vminute-minute)*60.
        vsecond  = second + remain_s

print*,'vdate:',tfield_r8(t), vyear,vmonth,vday,vhour,vminute,vsecond

        dates(t) = vyear*10000 + vmonth*100  + vday
        times(t) = vhour*10000 + vminute*100 + vsecond

      end do
!stop


    case ('365_day','noleap'   )
    !      =================== 
      print *,'noleap'

      ! Set start date to Jan 1st 00Z of start year
      ! https://astronomy.stackexchange.com/questions/2407/calculate-day-of-the-year-for-a-given-date
      N1 = floor(275 * month / 9.)
      ! N2 will equal 0 if month is less than 3, and will equal 1 if it is greater. This formula is to determine whether February has passed.
      N2 = floor((month + 9) / 12.)
      ! N3 will be equal to 2 if the year is not a leap year, and will be equal to 1 if it is a leap year. The math here is just to determine whether the current year happens to be a leap year.
      !N3 = (1 + floor((year - 4 * floor(year / 4.) + 2) / 3))
      !N  = N1 - (N2 * N3) + day - 30
      add_days = N1 - (N2 * 2) + day - 30

      add_secs = hour*3600 + minute*60 + second
print *,'add_days, add_secs:',add_days, add_secs

      month  = 1
      day    = 1
      hour   = 0
      minute = 0
      second = 0

      do t=1,nt
        remain_d = (tfield_r8(t)*cfac_sec+add_secs)/86400. + add_days  ! Full days of time passed
        vyear    =   year + (remain_d/365.)
        remain_d = remain_d - (vyear-year)*365. ! Full days passed since begining of current year

        if     (remain_d <=  31) then ; vmonth =  1 ; vday = remain_d
        elseif (remain_d <=  59) then ; vmonth =  2 ; vday = remain_d -  31
        elseif (remain_d <=  90) then ; vmonth =  3 ; vday = remain_d -  59
        elseif (remain_d <= 120) then ; vmonth =  4 ; vday = remain_d -  90
        elseif (remain_d <= 151) then ; vmonth =  5 ; vday = remain_d - 120
        elseif (remain_d <= 181) then ; vmonth =  6 ; vday = remain_d - 151
        elseif (remain_d <= 212) then ; vmonth =  7 ; vday = remain_d - 181
        elseif (remain_d <= 243) then ; vmonth =  8 ; vday = remain_d - 212
        elseif (remain_d <= 273) then ; vmonth =  9 ; vday = remain_d - 243
        elseif (remain_d <= 304) then ; vmonth = 10 ; vday = remain_d - 273
        elseif (remain_d <= 334) then ; vmonth = 11 ; vday = remain_d - 304
        else                          ; vmonth = 12 ; vday = remain_d - 334
        end if
!print*,'remain_d, vmonth:',remain_d, vmonth, vday

        remain_s = int(dmod(tfield_r8(t)*cfac_sec+add_days*86400+add_secs, 86400.d0))
        vhour    =   hour + remain_s/3600.
        remain_s = remain_s - (vhour-hour)*3600.
        vminute  = minute + remain_s/60.
        remain_s = remain_s - (vminute-minute)*60.
        vsecond  = second + remain_s

!print*,'vdate:',tfield_r8(t), vyear,vmonth,vday,vhour,vminute,vsecond

        dates(t) = vyear*10000 + vmonth*100  + vday
        times(t) = vhour*10000 + vminute*100 + vsecond

      end do

    case ('360_day'            )
    !      =================== 
      print *,'360_day'

      ! Set start date to Jan 1st 00Z of start year
      add_days = (month-1)*30 + (day-1)
      add_secs = hour*3600 + minute*60 + second
print *,'add_days, add_secs:',add_days, add_secs

      month  = 1
      day    = 1
      hour   = 0
      minute = 0
      second = 0

      do t=1,nt
        remain_d = (tfield_r8(t)*cfac_sec+add_secs)/86400. + add_days
        vyear    =   year + (remain_d/360.)
        remain_d = remain_d - (vyear-year)*360.
        vmonth   =  month + (remain_d/30.)
        remain_d = remain_d - (vmonth-month)*30.
        vday     =    day + remain_d

        remain_s = int(dmod(tfield_r8(t)*cfac_sec+add_days*86400+add_secs, 86400.d0))
        vhour    =   hour + remain_s/3600.
        remain_s = remain_s - (vhour-hour)*3600.
        vminute  = minute + remain_s/60.
        remain_s = remain_s - (vminute-minute)*60.
        vsecond  = second + remain_s

print*,'vdate:',tfield_r8(t), vyear,vmonth,vday,vhour,vminute,vsecond

        dates(t) = vyear*10000 + vmonth*100  + vday
        times(t) = vhour*10000 + vminute*100 + vsecond

      end do
  end select

  deallocate (tfield_r8)

end subroutine decode_time

! ----------------------------------------------------------------------------

! Routine to read main center field records (PN, PNS, VORT)
! -----------------------------------------
function input_file_read_main (field, varname, date, time)
  implicit none
  include "input_args.cdk"
 
  integer :: input_file_read_main

  real,              intent(out) :: field(ni,nj)
  integer,           intent(out) :: date, time
  character(len=4),  intent(in)  :: varname

  ! Local variables 
  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in
  integer :: xtype, ndims, dimids(3)

  integer :: d,dsize, v,id, l_nt
  character(len=64) :: pname, vname, dname
  character(len=64) :: unit_S
!print*,'In input_file_read_main, varname: ',varname
!print*,'datev, nt:',datev, nt

  ! Raise flag if last timestep was already read
  if (datev == nt) then
!print *,'Last timestep of current file read'
    input_file_read_main = -1


  ! Read main 3-D field
  elseif ( datev == 0 ) then


    ! Decode dates/times
    ! ==================
!    call decode_time (calendar_S, unit_S, tfield_r8, 33)
    call decode_time (iun_p)

!print*,'Read 3-D center field'

    ! Read main 3-D field
    ! ===================
    ! Make sure pressure field is found
    ! Name of pressure field
    select case (varname)
      case ('PN  ')
        pname = nf_pres
      case ('PNS ')
        pname = nf_pres_s
    end select

    ier = nf90_inquire(iun_p, ndims_in, nvars_in, ngatts_in, unlimdimid_in)

    id = 0
    do v=1,nvars_in
      ier = nf90_inquire_variable(iun_p,v,vname,xtype,ndims)
!print *,'pname,vname,ndims: ',trim(pname),' ',trim(vname),ndims
      if ( trim(vname) == trim(pname) ) then
        if ( ndims /= 3 ) then
          print *,''
          print *," Error: Pressure field '", trim(pname), "' was found, but"
          print *,'        it has',ndims,' dimensions instead of the required 3 (time, lat, lon)'
          print *,'        ----- ABORT -----'
          print *,''
          stop
        end if
        id = v
      end if
    end do

    if ( id == 0 ) then
      print *,''
      print *," Error: Pressure field '", trim(pname), "' could not get found."
      print *,'        ----- ABORT -----'
      print *,''
      stop
    end if

    ! Read main 3-D field
!print*,'Read 3-D center field'

    ! Make sure dimensions are correct
    ier = nf90_inquire_variable(iun_p,id,vname,xtype,ndims,dimids)
!print*,'dimids:',dimids

    ier = nf90_inquire_dimension(iun_p,dimids(1),dname,l_ni)
    ier = nf90_inquire_dimension(iun_p,dimids(2),dname,l_nj)
    ier = nf90_inquire_dimension(iun_p,dimids(3),dname,l_nt)

    if ( l_nt /= nt .or. &
         l_ni /= ni .or. &
         l_nj /= nj ) then
      print *,''
      print *," Error: The dimensions of ",trim(vname)," seen with 'ncdump' should be:"
      print *,'          (time,lat,lon) - the dimension names may be different but not the order.'
      print *,'        time: expected dimension: ',nt, ', read dimension:',l_nt
      print *,'        lat : expected dimension: ',nj, ', read dimension:',l_nj
      print *,'        lon : expected dimension: ',ni, ', read dimension:',l_ni
      print *,'        ----- ABORT -----'
      print *,''
      stop
    end if

    ! Allocate 3-D field
!    allocate (cfield_3d(ni,nj,nt))
    allocate (pfield_3d(ni,nj,nt))
    if (p_field == 'PNS ' ) allocate (psfield_3d(ni,nj,nt))
    allocate (vfield_3d(ni,nj,nt))
    if (plot_10mWind_L) allocate (wfield_3d(ni,nj,nt))

    ! Read main 3-D field
    ! -------------------
    ! Get field
!    ier = nf90_get_var(iun_p, id, cfield_3d)
    ier = nf90_get_var(iun_p, id, pfield_3d)

    ! Scale field with add_offset and scale_factor
    call add_offset_scale (iun_p, id, pfield_3d, ni,nj,nt)

    ! Check unit - final fields needs to be in hPa
    ier = nf90_get_att(iun_p, id, 'units', unit_S)
!print *,'unit:',unit_S
    if ( ier /= 0 ) then
      print *,''
      print *," Error: Attribute 'units' of pressure variable, ',pname,' not found."
      print *,'        ----- ABORT -----'
      print *,''
      stop
    end if

!    select case (trim(unit_S))
!      case ("Pa","pa")
    
    if (trim(unit_S) == "Pa" .or. trim(unit_S) == "pa" ) then
      print *,'Convert Pa to hPa'
      pfield_3d = pfield_3d * 0.01
    elseif (trim(unit_S) /= "hPa"  .and. &
            trim(unit_S) /= "hpa"  .and. &
            trim(unit_S) /= "mbar" .and. &
            trim(unit_S) /= "mBar") then
      print *,''
      print *," Error: 'units' of pressure variable, needs to be one of the following:"
      print *,"              'Pa', 'pa', 'hPa', 'hpa', 'mbar', 'mBar'"
      print *,'        Currently it is: ',trim(unit_S)
      print *,'                         ----- ABORT -----'
      print *,''
      stop
    end if

!stop

  end if

  if ( datev < nt ) then
    ! Select current timestep from 3-D field
    datev = datev + 1   ! next timestep
!    field = cfield_3d(:,:,datev)
    field = pfield_3d(:,:,datev)

    date  = dates(datev)
    time  = times(datev)

    if (.not. quiet_L) print*,'Now treating timestep (step,date,time): ',datev, date, time
  end if


end function input_file_read_main


! Routine to read records
! -----------------------
function input_file_read (field, varname, level, date, time, check_L)
  implicit none

  include "input_args.cdk"

  integer :: input_file_read
  real,             intent(out) :: field(ni,nj)
  character(len=4), intent(in)  :: varname
  integer,          intent(in)  :: level, date, time
  logical,          intent(in)  :: check_L

  ! Local variables
  character(len=64) :: varnam
  character(len=64) :: vname
  character(len=64) :: unit_S
  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in
  integer :: xtype, ndims

  integer :: iun, id, v

print*,'In input_file_read, varname, level: ',varname, level

  select case (varname)
    case ('PN  ')
      iun = iun_p
      id  = id_p
      varnam = nf_pres
    case ('UV  ') 
      iun = iun_w
      id  = id_w
      varnam = nf_wind
    case ('VORT','VORS')
      iun = iun_v
      id  = id_v
      varnam = nf_vort
  end select

  ! Read whole field for first timestep
  ! -----------------------------------

  if ( datev == 1 ) then

    ! Find variable id
    ier = nf90_inquire(iun, ndims_in, nvars_in, ngatts_in, unlimdimid_in)
    id  = 0
    do v=1,nvars_in
      ier = nf90_inquire_variable(iun,v,vname,xtype,ndims)
      if ( trim(vname) == trim(varnam) ) id = v
    end do

    if ( id == 0 ) then
      print *,''
      print *," Error: Field '", trim(varnam), "' could not get found."
      print *,'        ----- ABORT -----'
      print *,''
      stop
    end if

    ! Read 3-D field
    select case (varname)
      case ('PN  ')
        ! Read field
        ier = nf90_get_var(iun, id, psfield_3d)
        ! Scale field with add_offset and scale_factor
        call add_offset_scale (iun, id, psfield_3d, ni,nj,nt)

        ! Check unit - final fields needs to be in hPa
        ier = nf90_get_att(iun, id, 'units', unit_S)
!print *,'unit:',unit_S
        if ( ier /= 0 ) then
          print *,''
          print *," Error: Attribute 'units' of pressure variable, ',pname,' not found."
          print *,'        ----- ABORT -----'
          print *,''
          stop
        end if

        if (trim(unit_S) == "Pa" .or. trim(unit_S) == "pa" ) then
          print *,'Convert Pa to hPa'
          psfield_3d = psfield_3d * 0.01
        elseif (trim(unit_S) /= "hPa"  .and. &
                trim(unit_S) /= "hpa"  .and. &
                trim(unit_S) /= "mbar" .and. &
                trim(unit_S) /= "mBar") then
          print *,''
          print *," Error: 'units' of pressure variable, needs to be one of the following:"
          print *,"              'Pa', 'pa', 'hPa', 'hpa', 'mbar', 'mBar'"
          print *,'        Currently it is: ',trim(unit_S)
          print *,'                         ----- ABORT -----'
          print *,''
          stop
        end if


      case ('UV  ')
        ! Read field
        ier = nf90_get_var(iun, id, wfield_3d)
        ! Scale field with add_offset and scale_factor
        call add_offset_scale (iun, id, wfield_3d, ni,nj,nt)
      case ('VORT','VORS')
        ! Read field
        ier = nf90_get_var(iun, id, vfield_3d)
!print*,'input_file_read vfield_3d before:', vfield_3d(1,1,1)
        ! Scale field with add_offset and scale_factor
        call add_offset_scale (iun, id, vfield_3d, ni,nj,nt)
!print*,'input_file_read vfield_3d after :', vfield_3d(1,1,1)
    end select

  end if

  ! Select current timestep from 3-D field
  select case (varname)
    case ('PN  ')
      field = psfield_3d(:,:,datev)
    case ('UV  ')
      field = wfield_3d(:,:,datev)
    case ('VORT','VORS')
      field = vfield_3d(:,:,datev)
  end select

!print*,'input_file_read var: ',varname
!if (datev == 1 .and. varname == 'VORT') stop

end function input_file_read


! ============================================================================

subroutine read_mask (mfield,mfile)

! Subroutine to read mask

  implicit none

  ! Input variables
  real,                intent(OUT) :: mfield(ni,nj)
  character(len=1024), intent(IN)  :: mfile

  ! Local variables 
  integer :: mun
  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in
  character(len=64) :: vname, dname
  integer :: v,id,d1,d2, xtype,ndims
  integer, dimension (:), allocatable :: dimids

  ! Open the mask file
print *,'Open mask'
  mun = 20
  ier = nf90_open(mfile, nf90_nowrite, mun)

  if ( ier /= 0 ) then
    print *,''
    print *,' Something went wrong opening the mask file:'
    print *,'   ',trim(mfile)
    print *,'     ---------  ABORT  ----------'
    print *,''
    stop
  end if

  ! Check content of mask file
  ier = nf90_inquire(mun, ndims_in, nvars_in, ngatts_in, unlimdimid_in)
print*,ndims_in, nvars_in, ngatts_in, unlimdimid_in  


  ! Read mask
print *,'Read mask'

  ! Find mask ID
  id = 0
  do v=1,nvars_in
    ier = nf90_inquire_variable(mun,v,vname,xtype,ndims)
!print*,v,vname,xtype,ndims
    allocate (dimids(ndims))
    ier = nf90_inquire_variable(mun,v,vname,xtype,ndims,dimids)
print*,v,vname,xtype,ndims,dimids

    if (vname == "mask" .and. ndims == 2) then
      id = v
      d1 = dimids(1)
      d2 = dimids(2)
    end if

    deallocate (dimids)
  end do

  if (id == 0) then
    print *,''
    print *,' Error: Mask could not get read.'
    print *,'        Expected: 2-D field called "mask"'
    print *,'        ----- ABORT -----'
    print *,''
    stop
  end if

  ! Check that mask has the same size as data
  ier = nf90_inquire_dimension(mun,d1,dname,l_ni)
  ier = nf90_inquire_dimension(mun,d2,dname,l_nj)

  if ( l_ni /= ni .or. l_nj /= nj ) then
    print *,''
    print *,' Mask is not on the same field as data'
    print *,'     ---------  ABORT  ----------'
    print *,''
    stop
  end if

  ! Read mask
  ier = nf90_get_var(mun, id, mfield)

  ! Scale field with add_offset and scale_factor
  call add_offset_scale (mun, id, mfield, ni,nj,1)


print *,'Mask read'
  ier = nf90_close(mun)

end subroutine read_mask

! ============================================================================


subroutine add_offset_scale (iun, varid, field, l_ni,l_nj,l_nt)
  implicit none

  ! Input variables
  integer, intent(IN)  :: iun, varid, l_ni,l_nj,l_nt
  real, intent(INOUT)  :: field(l_ni,l_nj,l_nt)

  ! Local variables 
  integer :: xtype
  real :: offset, scalef
  character(len=32) :: att_name_S
  real*8              :: value_r8
  real                :: value_r
  integer             :: value_i
  integer*4           :: value_i4
  integer*8           :: value_i8
 
  ! Determine and apply scale_factor
  att_name_S = 'scale_factor'
  ier = nf90_inquire_attribute(iun, varid, att_name_S, xtype) !, len, attnum)
!print *,'scale_factor xtype, ier: ', xtype, ier

  if (ier == 0) then
    select case (xtype)
      case (NF90_DOUBLE)
        ier = nf90_get_att(iun, varid, att_name_S, value_r8)
!print *,'scale_factor value_r8:',value_r8
        field = field * value_r8
      case (NF90_FLOAT)
        ier = nf90_get_att(iun, varid, att_name_S, value_r)
        field = field * value_r
      case (NF90_SHORT)
        ier = nf90_get_att(iun, varid, att_name_S, value_i4)
        field = field * value_i4
      case (NF90_INT)
        ier = nf90_get_att(iun, varid, att_name_S, value_i)
        field = field * value_i
      case (NF90_INT64)
        ier = nf90_get_att(iun, varid, att_name_S, value_i8)
        field = field * value_i8
      case default
        print *,''
        print *,' Error: Attribute ',trim(att_name_S),' needs to be double, float, integer or short'
        print *,'        ----- ABORT -----'
        print *,''
        stop
    end select
  end if

  ! Determine and apply add_offset
  att_name_S = 'add_offset'
  ier = nf90_inquire_attribute(iun, varid, att_name_S, xtype) !, len, attnum)
!print *,'add_offset xtype: ', xtype

  if (ier == 0) then
    select case (xtype)
      case (NF90_DOUBLE)
        ier = nf90_get_att(iun, varid, att_name_S, value_r8)
!print *,'add_offset value_r8:',value_r8
        field = field + value_r8
      case (NF90_FLOAT)
        ier = nf90_get_att(iun, varid, att_name_S, value_r)
        field = field + value_r
      case (NF90_SHORT)
        ier = nf90_get_att(iun, varid, att_name_S, value_i4)
        field = field + value_i4
      case (NF90_INT)
        ier = nf90_get_att(iun, varid, att_name_S, value_i)
        field = field + value_i
      case (NF90_INT64)
        ier = nf90_get_att(iun, varid, att_name_S, value_i8)
        field = field + value_i8
      case default
        print *,''
        print *,' Error: Attribute ',trim(att_name_S),' needs to be double, float, integer or short'
        print *,'        ----- ABORT -----'
        print *,''
        stop
    end select
  end if

end subroutine add_offset_scale


! ============================================================================


! Subroutines to write 2-D fields with found storm centers of every timestep
! in RPN output file

! Routine to open output file
! ---------------------------
subroutine plot_centers_open (cfile)
  implicit none
  character(len=1024), intent(in) :: cfile
  oun = 21
!  ier = fnom(oun, cfile, 'STD+RND', 0)
!  ier = fstouv(oun,'STD+RND')
end subroutine plot_centers_open

! Routine to close output file
! ----------------------------
subroutine plot_centers_close ()
  implicit none
!  ier = fstfrm(oun)
!  ier = fclos (oun)
end subroutine plot_centers_close

! Routine to write 2-D center field
! ---------------------------------
subroutine plot_centers_write (cfield)
  implicit none
  real,                intent(in) :: cfield(ni,nj)
!  ier = fstecr(cfield,cfield,                       &
!               -nbits,oun,dateo,deet,npas,ni,nj,nk, &
!               ip1,ip2,ip3,typvar,'CENT',etiket,    &
!               grtyp,ig1,ig2,ig3,ig4,datyp,.false.)
end subroutine plot_centers_write 

! ============================================================================


subroutine open_track_density_file ()

  ! Open track density file and
  ! copy 0-, 1-, and 2-D dimensions and variables from input file except for time

  ! Copy all dimensions and variables with the names:
  !   lat, lon, rlat, rlon, rotated_pole

  !   NF90_OPEN                    ! open existing netCDF dataset
  !    NF90_INQUIRE                ! find out what is in it
  !       NF90_INQUIRE_DIMENSION   ! get dimension names, lengths
  !       NF90_INQUIRE_VARIABLE    ! get variable names, types, shapes
  !         NF90_INQ_ATTNAME       ! get attribute names
  !         NF90_INQUIRE_ATTRIBUTE ! get other attribute information
  !         NF90_GET_ATT           ! get attribute values
  !       NF90_GET_VAR             ! get values of variables
  !   NF90_CLOSE                   ! close netCDF dataset

!  character(len=64) :: pname, vname, dname
!
!    ! Name of pressure field
!    if ( varname == 'PN  ' ) then
!      pname = nf_pres
!    else
!      pname = nf_pres_s
!    end if
! 
!    ! Get number of dimensions, variables , global attributes
!    ier = nf90_inquire(iun_p, ndims_in, nvars_in, ngatts_in, unlimdimid_in)
!
!    ! Find id of center pressure field variable
!    id = 0
!    do v=1,nvars_in
!      ier = nf90_inquire_variable(iun_p,v,vname,xtype,ndims)
!!print *,'pname,vname,ndims: ',trim(pname),' ',trim(vname),ndims
!      if ( trim(vname) == trim(pname) ) then
!        id = v
!      end if
!    end do








! https://docs.unidata.ucar.edu/netcdf-fortran/current/f90-attributes.html#f90-copy-attribute-from-one-netcdf-to-another-nf90_copy_att
! NF90_COPY_ATT

  

end subroutine open_track_density_file

! ============================================================================


subroutine plot_track_density (t_density, tdfile)
  implicit none

! Writes field woth track density in RPB output file

  real,                intent(in) :: t_density(ni,nj)
  character(len=1024), intent(in) :: tdfile


  ! Open output RPN standard file for track density  
  dun = 22
!  ier = fnom(dun, tdfile, 'STD+RND', 0)
!  ier = fstouv(dun,'STD+RND')

  ! Write track density field
!  ier = fstecr(t_density,t_density,                &
!               -nbits,dun,dateo,deet,npas,ni,nj,1, &
!               ip1,ip2,ip3,typvar,'TDEN',etiket,   &
!               grtyp,ig1,ig2,ig3,ig4,datyp,.false.)

  ! Close file
!  ier = fstfrm(dun)
!  ier = fclos (dun)

end subroutine plot_track_density

! ============================================================================


subroutine get_LOLA ( global_L, glats,glons, plot_centers_L,plot_tracks_L )
!
! Author
! Katja Winger (May 2007)
!
! Description
! Subroutine which returns the latitude and longitude of each
! grid box for given : grtyp, ig1, ig2, ig3, ig4
!
  implicit none

! Input
  logical    , intent(in)  :: plot_centers_L, plot_tracks_L

! Output  
  logical    , intent(out) :: global_L
  real       , intent(out) :: glats(ni,nj)         ! 2D latitudes  on real globe
  real       , intent(out) :: glons(ni,nj)         ! 2D longitudes on real globe

  ! Local variables 
  integer :: ndims_in, nvars_in, ngatts_in, unlimdimid_in
  character(len=64) :: vname, dname
  integer :: d,v,i,j, id_lon,id_lat, xtype,ndims,dsize
  integer, dimension (:), allocatable :: dimids

  real      :: lats(nj)   , lons(ni)

  real*8    :: glats_r8(ni,nj), glons_r8(ni,nj)
  integer   :: glats_i4(ni,nj), glons_i4(ni,nj)
  integer*2 :: glats_i2(ni,nj), glons_i2(ni,nj)
  integer*8 :: glats_i8(ni,nj), glons_i8(ni,nj)


print *,'In get_LOLA'

  ier = nf90_inquire(iun_p, ndims_in, nvars_in, ngatts_in, unlimdimid_in)

  ! Try to read 2-D longitudes & latitudes
  ! --------------------------------------

  ! Loop over variables
  id_lon = 0
  id_lat = 0
  do v=1,nvars_in
    ier = nf90_inquire_variable(iun_p,v,vname,xtype,ndims)
print*,v,vname,xtype,ndims
   
    ! Only look at variables with 2 dimensions 
    if ( ndims == 2 ) then

      ier = nf90_inquire_variable(iun_p,v,vname,xtype,ndims,dimids)
print*,'2-D:',v,vname,xtype,ndims,dimids
 
      select case (vname)
        case ("lon","longitude","x")
print*,'Read 2-D longitudes'
          id_lon = v
          
          select case (xtype)
            case (NF90_SHORT)  ; ier = nf90_get_var(iun_p, v, glons_i2)
                                 glons = float(glons_i2)
            case (NF90_INT)    ; ier = nf90_get_var(iun_p, v, glons_i4)
                                 glons = float(glons_i4)
            case (NF90_FLOAT)  ; ier = nf90_get_var(iun_p, v, glons)
            case (NF90_DOUBLE) ; ier = nf90_get_var(iun_p, v, glons_r8)
                                 glons = glons_r8
            case (NF90_INT64)  ; ier = nf90_get_var(iun_p, v, glons_i8)
                                 glons = float(glons_i8)
            case default
              print *,''
              print *," Error: Type of longitude dimension variable is: ", xtype
              print *,"        but must be of type 3, 4, 5, 6 or 10:"
              print *,'        NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE,  NF90_INT64:'
              print *,'  ',    NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE,  NF90_INT64
              print *,'        ----- ABORT -----'
              print *,''
              stop
          end select

        case ("lat","latitude","y")
print*,'Read 2-D latitudes'
          id_lat = v
          select case (xtype)
            case (NF90_SHORT)  ; ier = nf90_get_var(iun_p, v, glats_i2)
                                 glats = float(glats_i2)
            case (NF90_INT)    ; ier = nf90_get_var(iun_p, v, glats_i4)
                                 glats = float(glats_i4)
            case (NF90_FLOAT)  ; ier = nf90_get_var(iun_p, v, glats)
            case (NF90_DOUBLE) ; ier = nf90_get_var(iun_p, v, glats_r8)
                                 glats = glats_r8
            case (NF90_INT64)  ; ier = nf90_get_var(iun_p, v, glats_i8)
                                 glats = float(glats_i8)
            case default
              print *,''
              print *," Error: Type of latitude dimension variable is: ", xtype
              print *,"        but must be of type 3, 4, 5, 6 or 10:"
              print *,'        NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE,  NF90_INT64:'
              print *,'  ',    NF90_SHORT,  NF90_INT,  NF90_FLOAT,  NF90_DOUBLE,  NF90_INT64
              print *,'        ----- ABORT -----'
              print *,''
              stop
          end select
      end select

      if ( id_lon /= 0 .and. id_lat /= 0 ) exit
    end if

  end do


  ! If 2-D lon/lat were not found create them
  if ( id_lon == 0 .or. id_lat == 0 ) then

    ! Try to read 1-D longitudes & latitudes
    ! --------------------------------------
    do d=1,ndims_in
      ier = nf90_inquire_dimension(iun_p,d,dname,dsize)
!print*,d,dname,dsize
      select case (dname)
        case ("lon","rlon","longitude","x")
          ier = nf90_get_var(iun_p, d, lons)
        case ("lat","rlat","latitude","y")
          ier = nf90_get_var(iun_p, d, lats)
      end select
    end do

    ! Then create 2-D lon/lat from the 1-D lon/lat
    do j=1,nj
      glons(:,j) = lons
    end do
    do i=1,ni
      glats(i,:) = lats
    enddo

  end if
print*,'glons(1,1),glats(1,1): ',glons(1,1),glats(1,1)
print*,'glons(ni,nj),glats(ni,nj): ',glons(ni,nj),glats(ni,nj)
!stop

  ! Check if grid is global in x-direction
  ! --------------------------------------
  call check_if_global (global_L, ni, nj, lats, lons)

print *,'global_L:',global_L
!  print *,' Latitudes : ', lats
!  print *,' Longitudes: ', lons
!stop

end subroutine get_LOLA

! ==============================================================================

subroutine check_if_global (global_L, ni, nj, lats, lons)
!
! Author
! Katja Winger (nov 2019)
!
! Description
! Check if grid is global in x-direction

  implicit none

! Input
  integer, intent(in)    :: ni, nj
  real   , intent(in)    :: lats(nj)             ! 1D latitudes  on rotated grid
  real   , intent(in)    :: lons(ni)             ! 1D longitudes on rotated grid
! Output
  logical, intent(out)   :: global_L             ! .true. : grid is global

! Local
  integer   j
  real      dx, next_lon

  print *,'Check if global in x-direction'

  global_L   = .false.
  dx       = lons(2) - lons(1)
  next_lon = lons(ni) + dx
  if ( next_lon .ge. 360. ) next_lon = next_lon - 360.

  if (( next_lon .ge. lons(1)-dx/4   .and.  &
        next_lon .le. lons(1)+dx/4 ) .or.   &
      ( next_lon .ge. lons(2)-dx/4   .and.  &
        next_lon .le. lons(2)+dx/4 )) then
    global_L    = .true.
  end if

!  if (global_L) then
!    do j=1,nj
!      if (glons(ni,j) .eq. 0.) glons(ni,j) = 360.
!    end do
!  end if

end subroutine check_if_global

! ==============================================================================

end module io_files_cdf_mod
