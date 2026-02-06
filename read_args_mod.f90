module read_args_mod
contains

subroutine read_input_arguments ()

  implicit none

  include "input_args.cdk"

  ! Variables to read input arguments
  integer             :: cur_arg, nargs, arg_len, status
  character(len=16)   :: key
  character(len=1024) :: val, option, dummy
  logical             :: already_real
  integer             :: i, f

! -----------------------------------------------------------------------

  ! Get number of given input arguments
  nargs = command_argument_count()
  if (nargs == 1) print_help_L = .true.

  ! Loop over input arguments
  cur_arg = 1     ! Counter for input arguments
  f  = 0          ! Counter for input files
  f1 = 9999       ! Number of first input argument containing an input file name
  f2 = 0          ! Number of last  input argument containing an input file name

  do while(cur_arg <= nargs)      ! process command line options
    call get_command_argument(cur_arg,option,arg_len,status)

    ! If argument is a key
    if ( option(1:1) == '-' ) then
      key = option

      if ( key == '-h' .or. key == '-help' .or. key == '--help' ) print_help_L = .true.
      if ( key == '-debug'   ) debug_L = .true.
      if ( key == '-quiet'   ) quiet_L = .true.
      if ( key == '-10mWind' ) plot_10mWind_L = .true.
      if ( key == '-geoWind' ) use_GeoWind_L  = .true.
!print *,'  key:',cur_arg,trim(key)

    ! argument is a value
    else
      val = option
!print *,'  val:',cur_arg,trim(val)

      ! s: input files
      if     (trim(key) == '-s' ) then
        f  = f + 1
        f1 = min(f1,cur_arg)
        f2 = max(f2,cur_arg)
        if (f == 1) ifile = val

      ! txt : output text file
      elseif (trim(key) == '-txt' ) then
        tfile = val

      ! centers : output file for centers (for debugging)
      elseif (trim(key) == '-centers' ) then
        cfile = val

      ! tracks : output file for track density (for debugging)
      elseif (trim(key) == '-tracks' ) then
        tdfile = val

      ! mask : mask file
      elseif (trim(key) == '-mask' ) then
        mfile = val

      ! pcrit: minimum pressure value for a center
      elseif(trim(key) == '-pcrit' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') pcrit
!        print *,' pcrit = ', pcrit

      ! vcrit: minimum vorticity value for a center
      elseif(trim(key) == '-vcrit' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) then
          do i=1,len_trim(dummy)
            if ( dummy(i:i) .eq. 'e' .or. dummy(i:i) .eq. 'E' ) then
              dummy = dummy(1:i-1) // '.' // dummy(i:len_trim(dummy))
              exit
            end if
          end do
          print *,' i = ',i, len_trim(dummy)
          if ( i-1 .eq. len_trim(dummy) ) then
            dummy = dummy(1:len_trim(dummy)) // '.'
          end if
        end if
        read (dummy,'(F12.4)') vcrit
!        print *,' vcrit = ', vcrit


      ! frame - maximum distance between pressure and vorticity center
      elseif(trim(key) == '-frame' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') frame
!        print *,' frame = ', frame

      ! distcc - maximum distance between two centers
      elseif(trim(key) == '-distcc' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') distcc
!        print *,' distcc = ', distcc

      ! min_hours - minimum time for which storm must last
      elseif(trim(key) == '-minh' ) then
        read (val,'(i8)') min_hours

      ! minimum pressure for track
      elseif(trim(key) == '-p_min' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') p_min
!        print *,' p_min = ', p_min

      ! v_lev - vorticity level
      elseif(trim(key) == '-v_lev' ) then
        if ( val .eq. '850hPa' ) then
          v_ip1 = 41744464   ! 850 hPa
        else
          v_ip1 = 26314400   !   1 sg
        end if
!        print *,' vorticity level : ',dummy(1:len_trim(dummy)),v_ip1

      ! w_lev - wind level (just for output)
      elseif(trim(key) == '-w_lev' ) then
        if ( val .eq. '850hPa' ) then
          v_ip1 = 41744464   ! 850 hPa
        else
          v_ip1 = 75597472   !  10 M
        end if

      ! span - Minimum distance the storm must travel
      elseif(trim(key) == '-span' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') span
!        print *,' span = ', span

      ! lon_W - Indices of window to track storms in
      elseif(trim(key) == '-lon_W' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') lon_W
!        print *,' lon_W = ', lon_W

      ! lon_E - Indices of window to track storms in
      elseif(trim(key) == '-lon_E' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') lon_E
!        print *,' lon_E = ', lon_E

      ! lat_S - Indices of window to track storms in
      elseif(trim(key) == '-lat_S' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') lat_S
!        print *,' lat_S = ', lat_S

      ! lat_N - Indices of window to track storms in
      elseif(trim(key) == '-lat_N' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') lat_N
!        print *,' lat_N = ', lat_N

      ! v_field - Name of vorticity field
      elseif(trim(key) == '-v_field' ) then
        v_field = val
        if ( trim(v_field) /= 'VORT' .and. trim(v_field) /= 'VORS' ) then
          print *," 'v_field' needs to be 'VORT' (default) or 'VORS' "
          print *,'                ----- ABORT -----'
          stop
        end if
!        print *,' vorticity field : ',v_field

      ! p_field - Name of pressure field
      elseif(trim(key) == '-p_field' ) then
        p_field = val
        if ( trim(p_field) /= 'PNS' .and. trim(p_field) /= 'PN' ) then
          print *," 'p_field' needs to be 'PNS' (default) or 'PN' "
          print *,'                ----- ABORT -----'
          stop
        end if

      ! c_field - Name of field to look for storm centers
      elseif(trim(key) == '-c_field' ) then
        c_field = val
!        print *,' center field : ',c_field
        if ( c_field .ne. 'PNS'  .and. c_field .ne. 'PN' .and. &
             c_field .ne. 'VORT' .and. c_field .ne. 'VORS' ) then
          print *,' Name of field to look for storm centers not accepted'
          print *,' Possible names are: PNS, PN, VORT, VORS'
          print *,' Chosen name is: ',c_field
          print *,'   ----- ABORT -----'
          stop
        endif

      ! disttr - Maximum distance to track consecutive centers to form one track
      elseif(trim(key) == '-disttr' ) then
        dummy = val
        already_real = .false.
        do i=1,len_trim(dummy)
          if ( dummy(i:i) .eq. '.' ) then
            already_real = .true.
            exit
          end if
        end do
        if ( .not. already_real ) dummy = dummy(1:len_trim(dummy)) // '.'
        read (dummy,'(F12.4)') disttr
!        print *,' disttr = ', disttr

! NetCDF file specific variables
! ------------------------------

      ! nf_pres   - Name of variable for "real" sea level pressure
      elseif(trim(key) == '-nf_pres' ) then
        nf_pres = val

      ! nf_pres_s - Name of variable for smoothed sea level pressure 
      elseif(trim(key) == '-nf_pres_s' ) then
        nf_pres_s = val

      ! nf_vort   - Name of variable for vorticity field (smoothed or "real")
      elseif(trim(key) == '-nf_vort' ) then
        nf_vort = val

      ! nf_wind   - Name of variable for near surface wind speed
      elseif(trim(key) == '-nf_wind' ) then
        nf_wind = val
      
      else
        print *,''
        print *," Key '",trim(key),"' not known."
        print *,'   ----- ABORT -----'
        print *,''
        stop

      end if

    end if

    cur_arg = cur_arg + 1
  end do  ! End Loop over arguments

end subroutine read_input_arguments

! ======================================================================================

function get_filename(f)
  implicit none
  character(len=1024) :: get_filename
  integer, intent(in) :: f                 ! Number if input argument

  ! Variables to read input arguments
  integer :: arg_len, status

  call get_command_argument(f,get_filename,arg_len,status)
 
  return 

end function get_filename 

end module read_args_mod
